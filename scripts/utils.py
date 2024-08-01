from datetime import datetime, timedelta

def calculate_start_date(start_date, day_of_week):
    weekdays = [int(d) for d in day_of_week.split('\\')]
    while start_date.weekday()+2 not in weekdays:
        start_date += timedelta(days=1)
    return start_date

def calculate_end_date(start_date, day_of_week, week_count, number_of_make_up_sessions):
    weekdays = [int(d) for d in day_of_week.split('\\')]
    end_of_week = start_date
    while end_of_week.weekday() not in weekdays[1:]:
        end_of_week += timedelta(days=1)
    end_date = end_of_week + timedelta(weeks=week_count-1)
    end_date += timedelta(days=number_of_make_up_sessions)
    return end_date

def get_week_number(date):
    week_number = date.isocalendar()[1]
    return week_number

def is_study_day(today, day):
    return today.weekday() + 2 == day
