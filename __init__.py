#!usr/bin/env python2.7
from flask import Flask, render_template, request, flash, url_for, redirect, session
from flaskext.mysql import MySQL
import base64
from functools import wraps
import operator

app = Flask(__name__)
app.secret_key = 'A0Zr98j/3yX R~XHH!jmN]LWX/,?RT'

mysql = MySQL()

app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'Flask@2017'
app.config['MYSQL_DATABASE_DB'] = 'ctf'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql.init_app(app)


# Route protector(player)
def login_required(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('You need to login')
            return redirect(url_for('hello'))

    return wrap


# Route protector admin
def login_required_admin(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in_admin' in session:
            return f(*args, **kwargs)
        else:
            flash('You need to login as Admin first.')
            return redirect(url_for('hello'))

    return wrap


@app.route("/index")
@app.route("/")
def hello():
    return render_template("welcome.html")


# View function for the registration page
@app.route('/register/', methods=["GET", "POST"])
def register():
    teams_list = populate_teams()
    return render_template("registration.html", teams=teams_list)


# This performs the new player registration
@app.route('/registerUser/', methods=["GET", "POST"])
def register_page():
    error = None
    message = None
    try:
        if request.method == "POST":
            username = request.form.get('username')
            password = password_enc(str(request.form.get("password")))
            team = request.form.get('team_select')
            conn, c = connection()  # c is the cursor , conn is the connection object,##ORDER MATTERS!!##
            c.execute("SELECT * FROM userAccounts WHERE userName='%s'" % username) 
           # c.callproc('sp_createUser', (username, password, team))
            
            data = c.fetchall()
            if len(data) is 0:
                c.execute("INSERT INTO userAccounts(userName,password,teamName) VALUES(%s,%s,%s)",(username,password,team))
                conn.commit()
                flash("Registration Successful,Please log in to continue")
                return render_template("welcome.html")
            else:
                error = "Username already exists"
                return render_template("registration.html", teams=populate_teams(),
                                       error=error)

        return ("okay")

    except Exception as e:
        return (str(e))


# View function for Players logging in
@app.route('/login_player', methods=['GET', 'POST'])
def login_player():
    error = None
    try:
        conn, c = connection()
        username = request.form.get('uname')
        password = request.form.get('pwrd')
        c.execute("SELECT userName FROM userAccounts WHERE userName = '%s'" % username)
        temp = c.fetchall()

        if len(temp) > 0:
            c.execute("SELECT password FROM userAccounts WHERE userName = '%s'" % username)
            temp_pass = c.fetchone()
            if password_dec(temp_pass[0]) == password:
                # session handler
                session['logged_in'] = True
                session['user_name'] = username
                c.execute("SELECT catName,question,puzzleName FROM puzzleBoard")
                raw_tuple = c.fetchall()
                catQ_list = []
                for cat, q, p in raw_tuple:
                    print cat, q, p
                    catQ_list.append((cat, q, p))
                return render_template("puzzles.html",
                                       categories=populate_categories(),
                                       catQ_list=catQ_list,
                                       username=username,
                                       teamScore=populate_teamScore())
            else:
                error = "Incorrect Password"
                return render_template('welcome.html', error=error)
        else:
            error = "Username doesn't exist"
            return render_template('welcome.html', error=error)

    except Exception as e:
        return (str(e))


# View function for admins logging in
@app.route('/login_admin', methods=['GET', 'POST'])
def login_admin():
    error_admin = None
    teams_list = populate_teams()
    category_list = populate_categories()
    try:
        conn, c = connection()
        username = request.form.get('uname')
        password = request.form.get('pwrd')
        c.execute("SELECT userName FROM adminAccounts WHERE userName = '%s'" % username)
        temp = c.fetchall()
        if len(temp) > 0:
            c.execute("SELECT password FROM adminAccounts WHERE userName = '%s'" % username)
            temp_pass = c.fetchone()
            # Remember to compare with decoded (pass_dec(temp_pass[0]) if encoded pass is stored!!
            if temp_pass[0] == password:
                session['logged_in_admin'] = True
                return render_template("editTeam.html", teams=teams_list,
                                       categories=category_list)  # changed from editGameContent to editTeams
            else:
                error_admin = "Incorrect Password"
                return render_template('welcome.html', error_admin=error_admin)  # redirect(url_for("hello"))
        else:
            error_admin = "Username doesn't exist"
            return render_template('welcome.html', error_admin=error_admin)

    except Exception as e:
        return (str(e))

# Separate puzzleboard view for admin
@app.route('/puzzleB_adminView')
@login_required_admin
def puzzle_view_admin():
    conn, c = connection()
    c.execute("SELECT catName,question,puzzleName FROM puzzleBoard")
    raw_tuple = c.fetchall()
    catQ_list = []
    for cat, q, p in raw_tuple:
        print cat, q, p
        catQ_list.append((cat, q, p))
    return render_template("puzzles.html",
                           categories=populate_categories(),
                           catQ_list=catQ_list,
                           teamScore=populate_teamScore())


# PuzzleBoard
@app.route('/puzzles', methods=['GET', 'POST'])
@login_required
def puzzles():
    error_tried = None
    category_list = populate_categories()
    try:
        conn, c = connection()
        c.execute("SELECT catName,question,puzzleName FROM puzzleBoard")
        raw_tuple = c.fetchall()
        catQ_list = []
        for cat, q, p in raw_tuple:
            print cat, q, p
            catQ_list.append((cat, q, p))

        print "***JUST for DEBUGGING***"
        for cat, q, p in catQ_list:
            print cat, q, p
        print "************************"
        username = session['user_name']
        query = "Select teamName From userAccounts WHERE userName = '%s'" % username
        c.execute(query)
        teamname = c.fetchone()
        teamname = str(teamname[0])
        # save team attempt to answer question to database
        questionName = request.form.get('q')
        c.execute("SELECT `"+ questionName +"` FROM leaderBoard WHERE teamName='%s'"%teamname)
        tried_flag = c.fetchone()
        print '******triedFlag*******'
        print tried_flag
        print tried_flag[0]
        #print int(tried_flag)
        if tried_flag[0]==0:
            #set flag=1 so that future attempts are not credited
            c.execute("UPDATE leaderBoard SET `"+questionName+"`=1 WHERE teamName ='%s'"% teamname)
            print "after******query"
            solution = request.form.get('sol')
            c.execute("SELECT answer FROM puzzleBoard WHERE question = '%s'" % questionName)
            answer = c.fetchone()

            print "***JUST for DEBUGGING***"
            print 'breakP1'
            print "************************"
            if solution == answer[0]:
                print "***JUST for DEBUGGING***"
                print 'afterSession'
                print "************************"
                query = "SELECT points FROM puzzleBoard WHERE question = '%s'" % questionName
                c.execute(query)
                points = c.fetchone()
                points = points[0]
                query = "Select score FROM leaderBoard WHERE teamName = '%s'" % teamname
                c.execute(query)
                prePoints = c.fetchone()
                print "***JUST for DEBUGGING***"
                print 'breakP3'
                print "************************"
                prePoints = int(prePoints[0])
                points = points + prePoints
                points = str(points)
  		print "********DEBUg******"
                query="UPDATE leaderBoard SET score= " + points + " WHERE teamName= '%s'" % teamname
                print "*Update Query***"
                print query
                c.execute("UPDATE leaderBoard SET score= " + points + " WHERE teamName= '%s'" % teamname)
                conn.commit()
                return render_template("puzzles.html",
                               categories=populate_categories(),
                               catQ_list=catQ_list,
                               username=username,
                               teamScore=populate_teamScore())
        error_tried = 'Question already tried'
        return render_template("puzzles.html",
                               categories=populate_categories(),
                               catQ_list=catQ_list,
                               username=username,
                               teamScore=populate_teamScore(),
                               error_tried=error_tried)
    except Exception as e:
        return (str(e))


'''# View Leaderboard
@app.route('/leaderBoard', methods=['GET', 'POST'])
def leaderBoard():
    teamScore = populate_teamScore()
    # teamScore.sort(key=lambda tup: tup[1])
    print teamScore
    return render_template("leaderBoard.html", teamScore=populate_teamScore())
'''

# Deletes teams from database
@app.route('/delete_team', methods=['GET', 'POST'])
@login_required_admin
def delete_teams():
    error = None
    try:
        if request.method == "POST":
            teamname = request.form.get('team_select')
            conn, c = connection()  # c is the cursor , conn is the connection object,##ORDER MATTERS!!##
            c.execute("DELETE FROM teams where teamName = '%s'" % teamname)
            c.execute("DELETE FROM leaderBoard where teamName ='%s'"%teamname)
            c.execute("DELETE FROM userAccounts where teamName = '%s'"%teamname)
            conn.commit()
            return render_template("editTeam.html", teams=populate_teams(), categories=populate_categories(),
                                   error=error)

    except Exception as e:
        return (str(e))
    return render_template("editTeam.html", teams=populate_teams(), categories=populate_categories(), error=error)


# Adds teams to database
@app.route('/add_team', methods=['GET', 'POST'])
@login_required_admin
def add_teams():
    error_add_team = None
    try:
        if request.method == "POST":
            teamname = request.form.get('team_select')
            conn, c = connection()  # c is the cursor , conn is the connection object,##ORDER MATTERS!!##
            query = "SELECT teamName FROM teams WHERE teamName = '%s'" % teamname
            c.execute(query)
            data = c.fetchall()
            if len(data) is 0:
                '''query = "INSERT INTO teams (teamName, no_Players) VALUES(%s, %s)"
                args = (teamname, 0) #Not sure if this needs to be validated before sending to database'''
                c.execute("INSERT INTO teams (teamName, no_Players, score) VALUES(%s, %s, %s)", (teamname, 0, 0))
                c.execute("INSERT INTO leaderBoard (teamName) VALUES(%s)",(teamname))
                conn.commit()
                return render_template("editTeam.html", teams=populate_teams(), categories=populate_categories())
            else:
                error_add_team = "Team Name already exists"
                return render_template("editTeam.html", teams=populate_teams(), categories=populate_categories(),
                                       error_add_team=error_add_team)

    except Exception as e:
        return (str(e))


# Delete categories from database
@app.route('/delete_category', methods=['GET', 'POST'])
@login_required_admin
def delete_category():
    error = None
    try:
        if request.method == "POST":
            catname = request.form.get('category_select')
            conn, c = connection()  # c is the cursor , conn is the connection object,##ORDER MATTERS!!##
            c.execute("DELETE FROM categories where catName = '%s'" % catname)
            c.execute("DELETE FROM puzzleBoard where catName = '%s'"% catname)
            conn.commit()
            return render_template("editTeam.html", categories=populate_categories(), teams=populate_teams(),
                                   error=error)

    except Exception as e:
        return (str(e))
    #return render_template("editTeam.html", categories=populate_categories(), teams=populate_teams(), error=error)


# Adds categories to database
@app.route('/add_category', methods=['GET', 'POST'])
@login_required_admin
def add_category():
    error_add_cat = None
    try:
        if request.method == "POST":
            catname = request.form.get('category_select')
            conn, c = connection()  # c is the cursor , conn is the connection object,##ORDER MATTERS!!##
            query = "SELECT catName FROM categories WHERE catName = '%s'" % catname
            c.execute(query)
            data = c.fetchall()
            if len(data) is 0:
                '''query = "INSERT INTO teams (teamName, no_Players) VALUES(%s, %s)"
                args = (teamname, 0) #Not sure if this needs to be validated before sending to database'''
                c.execute("INSERT INTO categories (catName) VALUES(%s)", (catname))
                conn.commit()
                return render_template("editTeam.html", categories=populate_categories(), teams=populate_teams())
            else:
                error_add_cat = "Team Name already exists"
                return render_template("editTeam.html", categories=populate_categories(), teams=populate_teams(),
                                       error_add_cat=error_add_cat)

        return ("okay")
    except Exception as e:
        return (str(e))


# Adds questions to database
@app.route('/add_question', methods=['GET', 'POST'])
@login_required_admin
def add_question():
    error_add_q = None
    try:
        if request.method == "POST":
            catname = request.form.get('category_select')
            puzzlename = request.form.get('puzzleName')
            questionname = request.form.get('question')

            # check for redundant question names
            ptname = request.form.get('point')
            ptname = int(ptname)
            answername = request.form.get('answer')
            conn, c = connection()
            c.execute( "INSERT INTO puzzleBoard (question, catName, points, answer, puzzleName) "
                       "VALUES(%s, %s, %s, %s, %s)",
                        (questionname, catname, ptname, answername, puzzlename))
            query = "ALTER TABLE leaderBoard ADD '"+questionname+ "' VARCHAR(20)"
            print query
            c.execute("ALTER TABLE leaderBoard ADD `"+questionname+ "` INT(1) NOT NULL DEFAULT '0'")
            print 'here is good'
            c.execute("INSERT INTO leaderBoard(`"+questionname+ "`) VALUES(0)")
            conn.commit()
            return render_template("editTeam.html", categories=populate_categories(), teams=populate_teams())

    except Exception as e:
        return (str(e))  # Get questions from database
'''
@app.route('/get_question',methods=['GET', 'POST'])
@login_required_admin
def get_questions():
    error=None
    try:
        catname=request.form.get('category_select')
        c.execute("SELECT * FROM puzzleBoard WHERE  catName='%s'",% catname)
        q_list=c.fetchall()
        return render_template("editTeam.html", categories=populate_categories(),teams=populate_teams(),questions=q_list)    except Exception as e:
        return (str(e))
'''


@app.route('/get_question',methods=['GET', 'POST'])
@login_required_admin
def get_questions():
    error=None
    try:
        conn,c=connection()
        catname=request.form.get('category_select')
        c.execute("SELECT question FROM puzzleBoard WHERE  catName='%s'" % catname)
        q_list=c.fetchall()
        q_list_final=[]
        for q in q_list:
            print q
            print q[0]
            q_list_final.append(q[0])
        return render_template("editTeam.html", categories=populate_categories(),teams=populate_teams(),questions=q_list_final,selected_catName=catname)
    except Exception as e:
        return (str(e))


#delete question
@app.route('/delete_question', methods=['GET', 'POST'])
@login_required_admin
def delete_question():
    error = None
    try:
        if request.method == "POST":
            questionList = request.form.getlist('question_select')
            print questionList
            conn, c = connection()
            for question in questionList:
                print "***debugQuestion****"
                print question
                c.execute("DELETE FROM puzzleBoard where question = '%s'" % question)
                c.execute("ALTER TABLE leaderBoard DROP COLUMN `"+question+"`")
            conn.commit()
            return render_template("editTeam.html", categories=populate_categories(), teams=populate_teams(),
                                   error=error)

    except Exception as e:
        return (str(e))
    return render_template("editTeam.html", categories=populate_categories(), teams=populate_teams(), error=error)


# connection object and cursor
def connection():
    conn = mysql.connect()
    c = conn.cursor()
    return conn, c


# log_out view for player
@app.route("/log_out")
@login_required
def log_out():
    session.pop('logged_in')
    return redirect(url_for('hello'))


# log_out view for admin
@app.route("/log_out_admin")
@login_required_admin
def log_out_admin():
    session.pop('logged_in_admin')
    return redirect(url_for('hello'))


# Password Encrypt Function(base64)
def password_enc(password):
    hashed = base64.b64encode(password)
    return hashed


# Password Decrypt Function(base64)
def password_dec(temp_pass):
    decoded = base64.b64decode(temp_pass)
    return decoded


# This function fetches the current registered teams
def populate_teams():
    conn, c = connection()
    c.execute("SELECT teamName FROM teams")
    teams = c.fetchall()
    teams_list = []
    for team in teams:
        teams_list.append(team[0])
    return teams_list


# This function fetches the current categories
def populate_categories():
    conn, c = connection()
    c.execute("SELECT catName FROM categories")
    categories = c.fetchall()
    category_list = []
    for category in categories:
        category_list.append(category[0])
    return category_list


# This function fetches questions and questionIDs
def populate_questions(catname):
    conn, c = connection()
    c.execute("SELECT question,questionID FROM puzzleBoard WHERE catName = '%s'" % catname)
    questions = c.fetchall()
    question_list = []
    for question in questions:
        question_list.append(question[0])
    return question_list


def populate_teamScore():
    conn, c = connection()
    c.execute("SELECT teamName, score FROM leaderBoard")
    raw_tuple = c.fetchall()
    teamScore_list = []
    for teamName, score in raw_tuple:
        print teamName
        teamScore_list.append((teamName, score))
    teamScore_list.sort(key=operator.itemgetter(1), reverse=True)

    print teamScore_list
    return teamScore_list


if __name__ == "__main__":
    app.run(debug=True)
