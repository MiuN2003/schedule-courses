from scripts.data_preparation import load_data, push_data
from scripts.schedule_optimizer import optimize_schedule

if __name__ == "__main__":
    resources, courses, teachers = load_data()
    results = optimize_schedule(resources, courses)
    push_data(results)
