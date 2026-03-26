import requests #For interfacing with websites
import json
import time
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from pathlib import Path
from datetime import datetime
from dateutil import parser
import teacher_data #A file with all the credentials, a blank template is in the repository

debug_mode = False

#localize imported data
class_ids = teacher_data.class_IDs
cookies = teacher_data.cookies

#UPDATE - Represents last digit of year
semester = 6

#Headers for the web requests
ma_headers = {
    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64)`1 AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    "Accept":"text/html,application/json"
}

#Set the directories
data_dir = Path(__file__).resolve().parent/"data"
data_dir.mkdir(exist_ok=True)
rosters_dir = data_dir/"rosters"
rosters_dir.mkdir(exist_ok=True)
tasks_dir = data_dir/"task_data"
tasks_dir.mkdir(exist_ok=True)

def normalize_name(name):
    if "," in name:
        last, first = [part.strip() for part in name.split(",", 1)]
        return f"{first} {last}"
    else:
        return name

#Creates and saves to a JSON file a dictionary of name:student_id
def pull_math_academy_roster(grade):
    if grade == None:
        for grade_level in class_ids:
            pull_math_academy_roster(grade_level)
        return
    class_id = class_ids[grade]
    url = f"https://mathacademy.com/classes/{class_id}"
    response = requests.get(url,headers=ma_headers,cookies=cookies)
    soup = BeautifulSoup(response.text, "lxml")
    table = soup.find(id = "students")
    data = [row.find_all("td") for row in table.find_all("tr")]
    roster = {}
    for student in data[1:]:
        student_url = student[0].find('a').get('href')
        parts = urlparse(student_url).path.split('/')
        student_id = parts[-2]
        student_name = normalize_name(student[0].get_text(strip=True))
        roster[student_name]=student_id
    json.dump(roster, open(rosters_dir/("MA_Roster_"+str(grade)+".json"),"w"), indent = 4)
    

#Pulls the data from the activity page of a student
def pull_math_academy_assignment_data(grade = None, student = None):
    if grade == None:
        for grade_level in class_ids:
            pull_math_academy_assignment_data(grade_level, student)
        return
    class_id = class_ids[grade]
    if debug_mode:
        print(f"class_id = {class_id}")
    roster = json.load(open(rosters_dir/("MA_Roster_"+str(grade)+".json"),"r"))
    if student == None:
        for name in roster:
            pull_math_academy_assignment_data(grade, name)
            print(f"Pulled {name} assignment data")
        return
    url = f"https://mathacademy.com/classes/{class_id}/students/{roster[student]}/activity"
    response = requests.get(url,headers=ma_headers,cookies=cookies)
    if response.status_code != 200:
        print(f"Response Code Problem: {response.status_code}")
        exit()
    soup = BeautifulSoup(response.text, "lxml")
    tables = soup.find_all('table')
    task_table = None
    for table in tables:
        if len(table.find_all('tr')) > 20:
            task_table = table
    if not task_table:
        print("Error, no table long enough to be task table")
        exit()
    task_rows = task_table.find_all('tr')
    tasks = process_task_list(task_rows) #loads all currently visible tasks
    try: #Loads old tasks in case they fell off the bottom of the site
        with open(tasks_dir/(student+"_Task_List.json"),'r') as file:
            prior_tasks = json.load(file)
    except FileNotFoundError:
        prior_tasks = {}
    for task in prior_tasks:
        if task not in tasks:
            tasks[task] = prior_tasks[task]
    with open(tasks_dir/(student+"_Task_List.json"),'w') as file:
        json.dump(tasks,file, indent = 4)

#Adds tasks from the task_rows to tasks, breaking at the new year.
def process_task_list(task_rows):
    tasks = {}
    date = None
    for task_row in task_rows:
        if task_row.find(class_='dateHeader') != None:
            new_date = task_row.find(class_='dateHeader').text.split('\n')[2].strip()
            if date != None and parser.parse(date) < parser.parse(new_date):
                break
            else:
                date = task_row.find(class_='dateHeader').text.split('\n')[2].strip()
        elif date != None:
            task_id = task_row.get('id').split('-')[1]
            if '/' in task_row.find(class_='taskPointsColumn').text:
                points = int(task_row.find(class_='taskPointsColumn').text.strip().split('/')[0])
            else:
                points = int(task_row.find(class_='taskPointsColumn').text.strip().split(' ')[0])
            tasks[task_id] = {'points':points, 'date':date}
    return tasks
