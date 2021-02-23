import json

import requests
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from sqlalchemy import Integer, String
from sqlalchemy import Table, Column, Boolean, MetaData
from sqlalchemy import create_engine
from sqlalchemy.orm import mapper, Session


class CommandHandler(object):

    def __init__(self):
        self.commands = {"?": [self.help, "? [command]"],
                         "ping": [self.ping, "ping"],
                         "login": [self.login, "login <file>\n\tlogin <login> <password>"],
                         "find": [self.find, "find <project> [page]"],
                         "select": [self.select, "select <project> - project value is id_repo or name"],
                         "branch": [self.branch, "branch <project> - project value is id_repo or name"],
                         "files": [self.files, "files <project> <branch>"]
                         }
        # self.engine = create_engine('sqlite:///db.sqlite', echo=True)
        self.engine = create_engine('sqlite:///db.sqlite')
        self.connection = self.engine.connect()
        self.metadata = MetaData()
        self.session = Session()

        self.repo_table = Table('repo', MetaData(bind=None, schema="main"),
                                Column('id', Integer, primary_key=True, autoincrement=True),
                                Column('id_repo', Integer),
                                Column('name', String),
                                Column('full_name', String),
                                Column('private', Boolean),
                                Column('owner', String),
                                Column('url', String),
                                Column('branches_url', String), autoload=True, autoload_with=self.engine
                                )
        # self.user_table.create(self.engine)
        mapper(Project, self.repo_table)
        self.branch_table = Table('branch', MetaData(bind=None, schema="main"),
                                  Column('id', Integer, primary_key=True, autoincrement=True),
                                  Column('id_repo', Integer),
                                  Column('branch', String),
                                  Column('branch_name', String),
                                  Column('branches_url', String),
                                  Column('author_name', String),
                                  Column('files', String), autoload=True, autoload_with=self.engine
                                  )
        # self.branch_table.create(self.engine)

    def select_project(self, id_repo: int = 0, name: str = None):
        if id_repo != 0:
            select_st = self.repo_table.select().where(
                self.repo_table.c.id_repo == id_repo).limit(1)
        else:
            select_st = self.repo_table.select().where(
                self.repo_table.c.name == name).limit(1)
        res = self.connection.execute(select_st)
        for _row in res:
            return _row
        return None

    def select(self, line: str):
        args = line.split()
        try:
            number = int(args[1])
            project = self.select_project(id_repo=number)
            if project == None:
                print("Project not found")
                return
            print(project)
            return
        except Exception:
            if len(args) <= 1 or len(args[1]) == 0:
                print("Bad args, use `? select`")
                return
            name = args[1]
            project = self.select_project(name=name)
            if project == None:
                print("Project not found")
                return
            print(project)
            return

    def ping(self, line: str):
        print("pong")
        return

    def getCommandByName(self, line: str):
        for i in self.commands:
            if line.lower().startswith(i):
                return self.commands[i]
        return None

    def help(self, line: str):
        args = line.split()
        if len(args) == 1:
            for i in self.commands:
                print(i)
                print("\t", self.commands[i][1])
        elif len(args) == 2:
            command = self.getCommandByName(args[1])
            if command is None:
                print("command not found, use ?")
            else:
                print(command[1])
        else:
            print("bad args, use `? [command]`")

    def loginByFile(self, name: str):
        try:
            with open(name, "r") as file:
                data = json.load(file)
            self.loginByData(data["login"], data["password"])
        except FileNotFoundError:
            print("File not found")
        return

    def loginByData(self, login: str, password: str):
        print("Login: ", login)
        driver = webdriver.Firefox()
        driver.get("https://github.com/login")
        elem = driver.find_element_by_name("login")
        elem.send_keys(login)
        elem = driver.find_element_by_name("password")
        elem.send_keys(password)
        elem.send_keys(Keys.RETURN)
        return

    def login(self, line: str):
        args = line.split()
        if len(args) == 2:
            self.loginByFile(args[1])
        elif len(args) == 3:
            self.loginByData(args[1], args[2])
        else:
            print("Bad param. Use `? login`")
            return

    def getProjects(self, q: str, page: str = "0"):
        try:
            page_value = int(page)
        except ValueError:
            print("Page error")
            return
        allPage: bool = page_value == 0
        if allPage:
            page_value = 1

        flag = True
        projects = []
        write: int = 0
        while flag:
            print("Load page number " + str(page_value))
            size, projects_ = self.req(q, str(page_value))
            projects += projects_
            write += 100
            page_value += 1
            flag = False
            if allPage:
                if write < size:
                    flag = write < 1000
        return projects

    def req(self, q: str, page: str = "1"):
        r = requests.get(
            "https://api.github.com/search/repositories?q=" + q.replace(" ", "+") + "&page=" + page + "&per_page=100")
        projects = []
        # print(r.json())
        size = 0
        try:
            size: int = r.json()["total_count"]
            for i in r.json()["items"]:
                projects.append(
                    Project(i["id"], i["name"], i["full_name"], i["private"], i["owner"]["login"], i["html_url"],
                            i["description"], i["fork"], i["url"], i["branches_url"]))
        except Exception:
            print(r.json())
        return size, projects

    def find(self, line: str):
        args = line.split()
        if len(args) == 1:
            print("bad param. Use '? find'")
            return
        if args[1].startswith('"'):
            newargs = [args[0]]
            args.pop(0)
            name = ""
            flag = False
            number: int = 0
            for i in args:
                number += 1
                name += i.replace('"', '') + " "
                if i.endswith('"'):
                    newargs.append(name[:-1])
                    # find "test project" 1
                    # number == 2
                    if len(args) - 1 == number:
                        newargs.append(args[len(args) - 1])
                    flag = True
                    break
            args = newargs
            if not flag:
                print("bad find req. User '? find'")
                return

        print("rq prName:\"" + args[1] + "\"")
        if len(args) == 3:
            print("page = " + args[2])
            projects = self.getProjects(args[1], args[2])
        else:
            projects = self.getProjects(args[1])
        added = 0
        for i in projects:
            project: Project = i
            # print(project)

            select_st = self.repo_table.select().where(
                self.repo_table.c.id_repo == project.id_repo).limit(1)
            res = self.connection.execute(select_st)
            flag = False
            for i in res:
                flag = True
                break

            if flag:
                continue

            added += 1
            print("find " + str(project.id_repo) + ", " + project.full_name)
            ins = self.repo_table.insert().values(
                id_repo=project.id_repo,
                name=project.name,
                full_name=project.full_name,
                private=project.private,
                owner=project.owner,
                url=project.url,
                branches_url=project.branches_url
            )
            conn = self.engine.connect()
            conn.execute(ins)
        self.session.commit()
        print("find " + str(len(projects)) + " projects, added " + str(added))

    def branchExist(self, id_repo: int = 0, name: str = None):
        print("exist", id_repo)
        print("name", name)
        if id_repo == 0 and name == None:
            return False, None
        if id_repo == 0:
            select_st = self.branch_table.select().where(
                self.branch_table.c.branch == name).limit(1)
            res = self.connection.execute(select_st)
            flag = False
            branchs = []
            for i in res:
                flag = True
                branchs.append(i)

            if flag:
                return True, branchs
            return False, None
        else:
            select_st = self.branch_table.select().where(
                self.branch_table.c.id_repo == id_repo).limit(1)
            res = self.connection.execute(select_st)
            flag = False
            branchs = []
            for i in res:
                flag = True
                branchs.append(i)

            if flag:
                return True, branchs
            return False, None

    def branch(self, line):
        args = line.split()

        number = 0
        name = None

        try:
            number = int(args[1])
            project = self.select_project(id_repo=number)
            if project == None:
                print("Project not found")
                return
        except Exception:
            if len(args) <= 1 or len(args[1]) == 0:
                print("Bad args, use `? select`")
                return
            name = args[1]
            project = self.select_project(name=name)
            if project == None:
                print("Project not found")
                return

        flag, branchs = self.branchExist(name=name, id_repo=number)
        if flag:
            for i in branchs:
                print(i)
            return

        branch_url = project[6]
        r = requests.get(branch_url + "/branches")
        print(r.json())

        for i in r.json():
            req_branch = requests.get(branch_url + "/branches/" + i['name'])
            req_commit = requests.get(req_branch.json()['commit']['url'])
            print("commit", req_commit.json())
            files = ""
            for j in req_commit.json()['files']:
                files += j['filename'] + ", "
            print("req " + str(req_branch.json()))
            ins = self.branch_table.insert().values(
                id_repo=project[1],
                branch=project[2],
                branch_name=i['name'],
                branches_url=branch_url + "/branches/" + i['name'],
                author_name=req_branch.json()['commit']['commit']['author']['name'],
                files=files
            )
            conn = self.engine.connect()
            conn.execute(ins)
        self.session.commit()

    def files(self, line):
        args = line.split()

        number = 0
        name = None
        if len(line.split()) != 3:
            print("Bad args, use `? files`")
            return
        try:
            number = int(args[1])
            project = self.select_project(id_repo=number)
            if project == None:
                print("Project not found")
                return
        except Exception:
            if len(args) <= 1 or len(args[1]) == 0:
                print("Bad args, use `? files`")
                return
            name = args[1]
            project = self.select_project(name=name)
            if project == None:
                print("Project not found")
                return

        flag, branchs = self.branchExist(name=name, id_repo=number)
        if flag:
            for i in branchs:
                print(i)
                if i[3] == args[2]:
                    print(i[6])
                    return
        print("Branch not found")
        return

    def run(self):
        # engine.execute("select * from repo").scalar()
        while 1:
            line = str(input())
            if len(line) == 0:
                continue
            command = self.getCommandByName(line.split()[0])
            if command is None:
                print("command not found, use ?")
            else:
                command[0](line)


class Project():
    __tablename__ = 'repo'

    def __init__(self, id_repo: int, name: str, full_name: str, private: bool, owner: str, html_url: str,
                 description: str, fork: bool, url: str, branches_url: str):
        self.id_repo: int = id_repo
        self.name: str = name
        self.full_name: str = full_name
        self.private: bool = private
        self.owner: str = owner
        self.html_url: str = html_url
        self.desctiption: str = description
        self.fork: bool = fork
        self.url: str = url
        self.branches_url: str = branches_url

    def __repr__(self):
        return "<Project('%d', '%s', '%s', False, '%s', '%s', '%s')>" % (
            self.id_repo, self.name, self.full_name, self.owner, self.url, self.branches_url)


commandHandler = CommandHandler()
commandHandler.run()
# params = None
# with open("params.json", "r") as file:
#     params = json.load(file)
#
# driver.get("https://github.com/search?q=" + str(params["project_name"]).replace(" ", "+"))
# # https://github.com/search?p=101&q=testt&type=Repositories
# i = 0
# while True:
#     html_list = driver.find_element_by_class_name("repo-list")
#     items = html_list.find_elements_by_tag_name("li")
#     for item in items:
#         text = item.text
#         print(text)
#     i += 1
#     driver.get("https://github.com/search?p=" + str(i) + "&q=" + str(params["project_name"]).replace(" ",
#                                                                                                      "+") + "&type=Repositories")
#     sleep(2)
#     if "Page not found" in driver.page_source:
#         break
#
# print(driver.find_element_by_class_name("next_page"))
#
# assert "No results found." not in driver.page_source
# # driver.close()
