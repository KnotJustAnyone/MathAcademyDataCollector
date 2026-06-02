import teacher_data
import requests

#urls
canvas_domain = "https://pasadena.instructure.com"
course_domain = f"{canvas_domain}/api/v1/courses"

access_token = teacher_data.access_token
course_id = 65788

canvas_headers = {"Authorization": f"Bearer {access_token}"}

def main_menu():
    choice = 1
    while choice:
        print("Which task are we attempting?")
        print("0) None, Quit")
        print("1) List Assignments")
        print("2) List Students")
        print("3) List Assignments with Submissions Waiting")
        print("D) Debug Menu")
        if choice == "D":
            choice = -1
        try:
            choice = int(input())
        except:
            print("Invalid Choice")
            choice = 0
        tasks = [None,list_assignments,list_students, not_fully_submitted_assignments, debug_menu]
        if choice and choice < len(tasks):
            tasks[choice]()
    print("Goodbye")

def list_assignments():
    for assignment in get_assignments():
        print(f"{assignment['id']}:{assignment['name']}")

def not_fully_submitted_assignments():
    for assignment in get_assignments():
        submissions = get_submissions(assignment['id'])
        ungraded = []
        for submission in submissions:
            try:
                if submission['grade'] == None and submission['user_id'] != 60631: #Test Student id
                    ungraded.append(submission['user_id'])
            except:
                print("submission raises error")
                print(submission)
        if len(ungraded) > 0:
            print(f"{assignment['id']}:{assignment['name']}:{ungraded} ungraded")

def get_assignments():
    url = f'{course_domain}/{course_id}/assignments'
    params = {"per_page": 100}
    response = requests.get(url, headers=canvas_headers, params=params)
    keys = ['id', 'due_at', 'points_possible', 'name']
    return [{key:assignment[key] for key in keys} for assignment in response.json()]

def get_submissions(id):
    url = f'{course_domain}/{course_id}/assignments/{id}/submissions'
    params = {"per_page": 100}
    response = requests.get(url, headers=canvas_headers, params=params)
    return response.json()

def list_students():
    url = f'{course_domain}/{course_id}'

def debug_menu():
    print("Choose an option:")
    print("0) Return to main menu")
    choice = input()
    if choice == '0':
        return

if __name__=="__main__":
    main_menu()

