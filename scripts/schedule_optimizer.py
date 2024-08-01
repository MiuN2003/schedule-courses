import pandas as pd
from datetime import datetime, timedelta
from ortools.sat.python import cp_model
from scripts.utils import get_week_number, is_study_day

def optimize_schedule(resources, courses):
    # Lấy ngày hôm nay
    today = datetime.today()
    results = pd.DataFrame()

    while not courses[courses['end_date'] >= today].empty:

        # Lọc ra các khóa học đang diễn ra
        current_courses = courses[(courses['start_date'].apply(lambda x: x.date()) <= today.date()) &
                                (courses['end_date'].apply(lambda x: x.date()) >= today.date())]

        current_courses['is_study_day'] = current_courses['day'].apply(lambda x: is_study_day(today, x))

        # Lọc ra các khóa học có ngày học bằng với ngày hôm nay
        today_courses = current_courses[current_courses['is_study_day'] == True]

        # Cập nhật phòng học cho các khóa học online
        today_courses.loc[courses['type'] == 'Online', 'id_room'] = 0

        # Danh sách các khóa học online cần chuyển đổi
        online_courses_to_move = []
        unique_teachers = list(set(today_courses['R_L_teacher'].tolist() + today_courses['W_teacher'].tolist() + today_courses['S_teacher'].tolist()))

        for teacher in unique_teachers:
            teacher_courses = today_courses[(today_courses['R_L_teacher'] == teacher) |
                                            (today_courses['W_teacher'] == teacher) |
                                            (today_courses['S_teacher'] == teacher)]

            for shift in teacher_courses['schedule'].unique():
                current_shift_courses = teacher_courses[teacher_courses['schedule'] == shift]
                next_shift_courses = teacher_courses[teacher_courses['schedule'] == shift + 1]

                for current_course in current_shift_courses['name']:
                    for next_course in next_shift_courses['name']:
                        if (today_courses[today_courses['name'] == current_course]['type'].values[0] == 'Online' and
                            today_courses[today_courses['name'] == next_course]['type'].values[0] == 'Online'):
                            online_courses_to_move.extend((current_course, next_course))

        final_today_courses = today_courses[~today_courses['name'].isin(online_courses_to_move)]

        # Khởi tạo mô hình ràng buộc
        model = cp_model.CpModel()

        # Tạo các biến quyết định
        variables = {}
        for course in final_today_courses['name']:
            for resource in resources['name']:
                variables[(course, resource)] = model.NewBoolVar(f'x_{course}_{resource}')

        # Hàm mục tiêu: tối đa hóa ưu tiên của phòng học, với các khóa online có độ ưu tiên thấp
        model.Maximize(sum(variables[(course, resource)] * resources.loc[resources['name'] == resource, 'priority'].values[0]
                        for course in final_today_courses['name']
                        for resource in resources['name']))

        # Ràng buộc: mỗi ca thì mỗi phòng chỉ chứa một khóa học
        for resource in resources['name']:
            for shift in final_today_courses['schedule'].unique():
                model.Add(sum(variables[(course, resource)]
                            for course in final_today_courses[final_today_courses['schedule'] == shift]['name']) <= 1)

        # Ràng buộc: mỗi khóa học chỉ sử dụng 1 phòng học
        for course in final_today_courses['name']:
            model.Add(sum(variables[(course, resource)] for resource in resources['name']) == 1)

        # Ràng buộc: số học sinh không vượt quá sức chứa của phòng
        for course in final_today_courses['name']:
            for resource in resources['name']:
                model.Add(variables[(course, resource)] * final_today_courses.loc[final_today_courses['name'] == course, 'students'].values[0] <=
                        resources.loc[resources['name'] == resource, 'capacity'].values[0])

        # Ràng buộc: giữ nguyên các lớp đã được xếp phòng
        for course in final_today_courses[final_today_courses['id_room'] != 0]['name']:
            assigned_room = final_today_courses.loc[final_today_courses['name'] == course, 'id_room'].values[0]
            model.Add(variables[(course, resources.loc[resources['id'] == assigned_room, 'name'].values[0])] == 1)

        # Ràng buộc: không xung đột với các lớp sau trong cùng một ca
        for shift in final_today_courses['schedule'].unique():
            shift_courses = final_today_courses[final_today_courses['schedule'] == shift]
            for i, course1 in enumerate(shift_courses['name']):
                for j, course2 in enumerate(shift_courses['name']):
                    if i < j:
                        for resource in resources['name']:
                            model.Add(variables[(course1, resource)] + variables[(course2, resource)] <= 1)

        # Ràng buộc: giáo viên dạy 2 ca liên tiếp được ưu tiên xếp phòng cùng hoặc cùng tầng
        # unique_teachers = set(sum(today_courses['list_teacher'], []))
        unique_teachers = list(set(today_courses['R_L_teacher'].tolist() + today_courses['W_teacher'].tolist() + today_courses['S_teacher'].tolist()))

        for teacher in unique_teachers:
            # teacher_courses = final_today_courses[final_today_courses['list_teacher'].apply(lambda x: teacher in x)]
            teacher_courses = final_today_courses[(final_today_courses['R_L_teacher'] == teacher) |
                                                (final_today_courses['W_teacher'] == teacher) |
                                                (final_today_courses['S_teacher'] == teacher)]
            current_shift_courses = teacher_courses[teacher_courses['schedule'] == 4]
            next_shift_courses = teacher_courses[teacher_courses['schedule'] == 5]

            for current_course in current_shift_courses['name']:
                for next_course in next_shift_courses['name']:
                    assigned = False
                    for resource1 in resources['name']:
                        for resource2 in resources['name']:
                            same_floor = (resources.loc[resources['name'] == resource1, 'floor'].values[0] ==
                                        resources.loc[resources['name'] == resource2, 'floor'].values[0])
                            model.Add(variables[(current_course, resource1)] + variables[(next_course, resource2)] <= 1 + same_floor)
                            assigned = True
                    # Nếu không thể xếp cùng phòng hoặc cùng tầng, vẫn phải được xếp ở đâu đó
                    if not assigned:
                        model.Add(sum(variables[(current_course, resource)] for resource in resources['name']) == 1)
                        model.Add(sum(variables[(next_course, resource)] for resource in resources['name']) == 1)

        # Giải bài toán
        solver = cp_model.CpSolver()
        status = solver.Solve(model)

        # Kiểm tra kết quả và cập nhật id_room
        if status == cp_model.OPTIMAL:
            for course in final_today_courses['name']:
                for resource in resources['name']:
                    if solver.Value(variables[(course, resource)]) == 1:
                        if courses.loc[courses['name'] == course, 'type'].values[0] == 'Offline':
                            id_room = resources.loc[resources['name'] == resource, 'id'].values[0]
                            courses.loc[courses['name'] == course, 'id_room'] = id_room
                            today_courses.loc[today_courses['name'] == course, 'id_room'] = id_room
                        else:
                            id_room = resources.loc[resources['name'] == resource, 'id'].values[0]
                            courses.loc[(courses['name'] == course) & (courses['day'] == today.weekday()+2), 'id_room'] = id_room
                            today_courses.loc[(today_courses['name'] == course) & (today_courses['day'] == today.weekday()+2), 'id_room'] = id_room

        # In ra các khóa học đã được xếp lịch sau khi tối ưu
        optimized_today_courses = today_courses
        optimized_today_courses['week'] = get_week_number(today.date())
        # Lưu kết quả vào results
        results = pd.concat([results, optimized_today_courses])

        # Tính ngày học tiếp theo
        today += timedelta(days=1)

    return results