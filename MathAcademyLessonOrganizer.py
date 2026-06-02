import requests #For interfacing with websites
import teacher_data
from bs4 import BeautifulSoup
import json

home_url = "https://mathacademy.com/"
courses_url = home_url+"courses/"
courses = ["prealgebra","integrated-math-i-honors","integrated-math-ii-honors","integrated-math-iii-honors","ap-calculus-bc"]
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
    choice = 1
    while choice:
        print("Which task are we attempting?")
        print("1) Extract Topic Tree for a course (In Progress)")
        print("Future Tasks:")
        print("Gather Topics for a specific grade with prerequisites")
        print("Find terminal tasks")
        print("Form percent progress targets")
        print("Optimize goals for various stages")
        choice = input()
        if choice == '1':
            topics = course_topics(0)
            for topic in topics:
                topics[topic]['prereqs'] = find_prereqs(topic)
            with open(tree_dir/"PrealgebraTree.json",'w') as file:
                json.dump(topics,file,indent=4)

def course_topics(course):
    if isinstance(course,int):
        course = courses[course]
    url = courses_url+course
    response = requests.get(url,headers=ma_headers,cookies=cookies)
    soup = BeautifulSoup(response.text, "lxml")
    content = soup.find(id = "contentFrame")
    links = content.find_all("a",class_="topicNameLink")
    topics = {}
    for link in links:
        topic_id = int(link.get("href").split('/')[-1])
        name = link.text
        if name == None:
            print(link)
            exit()
        topics[topic_id] = {'name':name}
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

def explore_soup(tag, depth=0):
    if tag.name:
        print("  " * depth, tag.name, tag.get("id"), tag.get("class"))

        if depth < 3:
            for child in tag.children:
                explore_soup(child, depth + 1)

if __name__ == "__main__":
    main_menu()