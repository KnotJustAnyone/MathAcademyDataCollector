import requests #For interfacing with websites
import teacher_data
from bs4 import BeautifulSoup
import json

"""
Finish modifying the course topics function to incorporate the save into it.
"""

home_url = "https://mathacademy.com/"
courses_url = home_url+"courses/"
course_names = ["prealgebra","integrated-math-i-honors","integrated-math-ii-honors","integrated-math-iii-honors","ap-calculus-bc"]
ma_headers = {
    "User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64)`1 AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    "Accept":"text/html,application/json"
}
cookies = teacher_data.cookies

from pathlib import Path

tree_dir = Path(__file__).resolve().parent/"trees"
tree_dir.mkdir(exist_ok=True)

def main_menu():
    print("This code is being designed to gather the prerequsite tree from MathAcademy.com")
    choice = ''
    while choice == '':
        print("Which task are we attempting? Empty response exits")
        print("1) Extract Topic Tree for a course")
        print("2) Remove unnecesary prerequisites")
        print("3) Create Full Grade Topic Tree")
        print("4) Analyze Tree")
        print("Future Tasks:")
        print("Find terminal tasks")
        print("Form percent progress targets")
        print("Optimize goals for various stages")
        choice = input()
        if choice == '':
            return None
        if choice[0] == '1':
            if len(choice) > 1:
                course = int(choice[1:])
            else:
                course = choose_course()
            course_topics(course)
            choice = ''
        elif choice[0] == '2':
            trees = [tree for tree in tree_dir.iterdir()]
            if len(choice) > 1:
                tree = trees[int(choice[1:])]
            else:
                tree = choose_tree()
            clear_assumed_prerequisites(tree)
            choice = ''
        elif choice[0] == '3':
            choice = choice[1:]
            if len(choice) > 0:
                grade = int(choice[0])
            else:
                grade = input("Which Grade:")
                try:
                    grade = int(grade)
                except:
                    grade = None
            grade_topic_tree(grade)
            choice = ''
        elif choice[0] == '4':
            choice = choice[1:]
            trees = [tree for tree in tree_dir.iterdir()]
            if len(choice) > 0:
                tree = trees[int(choice[0])]
                choice = choice[1:]
            else:
                tree = choose_tree()
            analyze_tree(tree,choice)
            choice = ''

def choose_course():
    print("Which course do you want to apply it to?")
    course = None
    while course == None:
        for i in range(len(course_names)):
            print(f"{i}) {course_names[i]}")
        course = input()
        try:
            course = int(course)
        except:
            course = None
            print("Invalid input, try again")
    return course

def choose_tree():
    trees = [tree for tree in tree_dir.iterdir()]
    print("Which tree do you want to manipulate?")
    for i in range(len(trees)):
        print(f"{i}: {trees[i].stem}")
    print("Type nothing or anything else to escape")
    choice = input()
    try:
        choice = int(choice)
        if choice < len(trees):
            return trees[choice]
        else:
            return None
    except:
        return None

def course_topics(course):
    course_name = course_names[course]
    topics = {}
    try:
        with open(tree_dir/f"{course_name}.json",'r') as file:
            topics = json.load(file)
        print(f"{course_name} Data Found")
        reload = input("Regenerate Data (y/n)?")
        if reload.lower() != 'y':
            return topics
    except:
        print(f"Data not found, Generating Tree for {course_name}")
    url = courses_url+course_name
    response = requests.get(url,headers=ma_headers,cookies=cookies)
    soup = BeautifulSoup(response.text, "lxml")
    content = soup.find(id = "contentFrame")
    if content == None:
        print("Content is None Error")
        print(f"Soup gave {soup}")
        print(f"url was {url}")
        quit()
    links = content.find_all("a",class_="topicNameLink")
    for link in links:
        topic_id = int(link.get("href").split('/')[-1])
        name = link.text
        if name == None:
            print(link)
            exit()
        topics[topic_id] = {'name':name, 'course':course_name}
    for topic in topics:
        topics[topic]['prereqs'] = find_prereqs(topic)
    with open(tree_dir/f"{course_name}.json",'w') as file:
        json.dump(topics,file,indent=4)
    return topics

def find_prereqs(topic):
    print(f"Finding prerequisites for topic {topic}")
    prereqs = []
    url = home_url+f"topics/{topic}"
    response = requests.get(url,headers=ma_headers,cookies=cookies)
    soup = BeautifulSoup(response.text, "lxml")
    sidebar = soup.body.find(id = 'sidebar')
    prerequisite_links = sidebar.find_all('a',recursive=True)
    for link in prerequisite_links:
        try:
            prereqs.append(link.get('href').split('-')[-1])
        except:
            pass
    return prereqs

def clear_assumed_prerequisites(tree):
    with open(tree,'r') as file:
        topics = json.load(file)
    for topic in topics:
        topics[topic]["prereqs"] = [prereq for prereq in topics[topic]["prereqs"] if prereq in topics]
    with open(tree_dir/f"{tree.stem+"Start"}.json",'w') as file:
        json.dump(topics,file,indent=4)

def grade_topic_tree(grade = None):
    if grade == None:
        grade_topic_tree(6)
        grade_topic_tree(7)
        return
    if grade == 6:
        topics = {}
        for course in range(3):
            topics.update(course_topics(course))
        with open(tree_dir/f"grade{grade}Tree.json",'x') as file:
            json.dump(topics,file,indent=4)
    if grade == 7:
        topics = {}
        for course in range(3,4):
            topics.update(course_topics(course))
        with open(tree_dir/f"grade{grade}Tree.json",'x') as file:
            json.dump(topics,file,indent=4)

def assign_depth(topic,topics):
    depth = 1
    for prereq in topics[topic]['prereqs']:
        if topics[prereq]['depth']:
            depth = max(depth,topics[prereq]['depth']+1)
        else:
            depth = max(depth,assign_depth(prereq,topics)+1)
    topics[topic]['depth'] = depth
    return depth

def find_terminal_topics(topics):
    prerequisites = set()
    for topic in topics:
        prerequisites.update(topics[topic]["prereqs"])
    terminal_topics = []
    for topic in topics:
        if topic not in prerequisites:
            terminal_topics.append(topic)
    return terminal_topics

def analyze_tree(tree,choice):
    with open(tree,'r') as file:
        topics = json.load(file)
    while True:
        if choice == '':
            print("How would you like to analyze it? Empty response returns to main menu.")
            print("1: Count Topics")
            print("2: List Terminal Tasks")
            print("3: Assign Task Depth")
            print("4: Identify prunable tasks (highest depth leaf nodes)")
            choice = input()
        if choice == '':
            return None
        if choice[0] == '1':
            print(f"Tree has {len(topics)} topics to cover.")
            choice = ''
        elif choice[0] == '2':
            terminal_topics = find_terminal_topics(topics)
            for topic in terminal_topics:
                print(f"{topic}:{topics[topic]['name']}:Depth {topics[topic]['depth']}")
            print(f"There are {len(terminal_topics)} terminal topics")
            choice = ''
        elif choice[0] == '3':
            for topic in topics:
                topics[topic]['depth'] = None
            for topic in topics:
                assign_depth(topic,topics)
            with open(tree,'w') as file:
                json.dump(topics,file,indent=4)
            print("Depths Assigned")
            choice = ''
        elif choice[0] == '4':
            terminal_topics = find_terminal_topics(topics)
            leaf_nodes = []
            for topic in terminal_topics:
                if len(topics[topic]['prereqs']) < 2:
                    leaf_nodes.append(topic)
            for topic in leaf_nodes:
                print(f"{topic}:{topics[topic]['name']}")
            choice = ''
        else:
            choice = ''
    return None

def explore_soup(tag, depth=0):
    if tag.name:
        print("  " * depth, tag.name, tag.get("id"), tag.get("class"))

        if depth < 3:
            for child in tag.children:
                explore_soup(child, depth + 1)

if __name__ == "__main__":
    main_menu()