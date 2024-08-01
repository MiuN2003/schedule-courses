import pandas as pd

def load_data():
    resources = pd.read_csv("resources.csv")
    courses = pd.read_csv('courses.csv')
    teachers = pd.read_excel('teachers.xlsx')

    return resources, courses, teachers