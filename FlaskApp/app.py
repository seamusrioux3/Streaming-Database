from flask import Flask, render_template, request, url_for, session, redirect, jsonify
from datetime import datetime, timedelta
from flask_pymysql import MySQL
import re
import pymysql
import random
import sys
import db_config

app = Flask(__name__)

app.secret_key = 'streamtime'

#Set up pymysql connection arguments
pymysql_connect_kwargs = {'user': db_config.DB_USER, 
                          'password': db_config.DB_PASS, 
                          'host': db_config.DB_SERVER,
                          'database': db_config.DB}

app.config['pymysql_kwargs'] = pymysql_connect_kwargs
mysql = MySQL(app)


"""

Login Page

"""
@app.route("/")
@app.route("/login", methods=['GET', 'POST'])
def login():
    #Error message
    errorMessage = ''
    #Check if email and phone number is in POST
    if request.method == 'POST' and 'email' in request.form and 'phone' in request.form:

        # Create variables for easy access
        email = request.form['email']
        phone = request.form['phone']

        # Check if account exists using MySQL Function findUser
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT findUser(%s, %s) as foundUser', (email, phone,))
        account = cursor.fetchone()[0]

        # If account exists in accounts table in out database
        if account:
            # Session data with id and loggedin information
            session['loggedin'] = True
            session['id'] = account
            # Redirect to home page
            return redirect(url_for('home'))
        else:
            # Account doesnt exist or username/password incorrect
            errorMessage = 'Invalid username/password!'
    # Show the login form with message
    return render_template('login.html', errorMessage = errorMessage)


"""

Logout Page

"""
@app.route('/logout')
def logout():
    # Remove session data, this will log the user out
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    # Redirect to login page
    return redirect(url_for('login'))



"""

Register Page

"""

@app.route('/register', methods=['GET', 'POST'])
def register():
    # Output message if something goes wrong...
    msg = ''
    #Get payment plan information for registration
    cursor = mysql.connection.cursor(pymysql.cursors.DictCursor)
    cursor.callproc('getPaymentPlans')
    paymentPlans = cursor.fetchall()
    print(paymentPlans)
    # Check if firstname, lastname, email, phone and plan are selected
    if (request.method == 'POST' and 'firstName' in request.form and 
        'lastName' in request.form and 'email' in request.form and 
        'phone' in request.form and 'plan' in request.form): 
        # Create variables for easy access
        firstName = request.form['firstName']
        lastName = request.form['lastName']
        email = request.form['email']
        phone = request.form['phone']
        plan = request.form['plan']
        print(request.form)

        # Check if account exists in database
        cursor.execute('SELECT findUser(%s, %s) as foundUser', (email, phone,))
        account = cursor.fetchone()

        # If account exists show error and validation checks
        if account['foundUser']:
            msg = 'Account already created!'
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address!'
        elif not re.match(r'[A-Za-z]+', firstName):
            msg = 'Name must cotain only characters!'
        elif not re.match(r'[A-Za-z]+', lastName):
            msg = 'Name must cotain only characters!'
        elif not firstName or not lastName or not email or not phone or not plan:
            msg = 'Please fill out the form!'
        else:
            # Account doesnt exists and the form data is valid, now insert new account into accounts table
            cursor.execute('call createUser(%s, %s, %s, %s, %s)',
                           (firstName, lastName, email, phone, plan))
            mysql.connection.commit()
            msg = 'You have successfully registered!'

            # Check if account exists using MySQL Function findUser
            cursor = mysql.connection.cursor()
            cursor.execute('SELECT findUser(%s, %s) as foundUser', (email, phone,))
            account = cursor.fetchone()[0]

            # If account exists in accounts table in out database
            if account:
                # Session data with id and loggedin information
                session['loggedin'] = True
                session['id'] = account
                # Redirect to home page
                return redirect(url_for('home'))

    elif request.method == 'POST':
        # Form is empty... (no POST data)
        msg = 'Please fill out the form!'
    # Show registration form with message (if any)
    return render_template('register.html', msg = msg, paymentplans = paymentPlans)


"""

Home Page and dependencies

"""
def calculateTotalDuration(playlistsongs):
    totalTime = 0
    for p in playlistsongs:
        if not totalTime:
            totalTime = p['duration']
        else:
            totalTime += p['duration']
    return totalTime

@app.route('/home', methods = ['GET', 'POST'])
def home():
    # Check if user is loggedin
    if 'loggedin' in session:
        if request.method == 'POST' and 'new' in request.form:
            return redirect(url_for('newplaylist'))
        
        if request.method == 'POST' and 'view' in request.form:
            playlistId = request.form['view']
            return redirect(url_for('playlist', playlist_id=playlistId))

        if request.method == 'POST' and 'remove' in request.form:
            playlistId = request.form['remove']
            cursor = mysql.connection.cursor(pymysql.cursors.DictCursor)
            cursor.execute('CALL removePlaylist(%s)', (playlistId))
            mysql.connection.commit()

        cursor = mysql.connection.cursor(pymysql.cursors.DictCursor)
        cursor.execute('CALL getPlaylistsUser(%s)', (session['id']))
        playlists = list(cursor.fetchall())

        for p in playlists:
            cursor = mysql.connection.cursor(pymysql.cursors.DictCursor)
            cursor.execute('CALL getPlaylistSongs(%s)', (p['playlistId']))
            playlistsongs = list(cursor.fetchall())
            p['duration'] = calculateTotalDuration(playlistsongs)
        return render_template('home.html', playlists = playlists)
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))


"""

Profile Page and dependencies

"""
@app.route('/profile', methods = ['POST', 'GET'])
def profile():
    # Check if user is loggedin
    if 'loggedin' in session:
        if request.method == 'POST' and 'edit' in request.form:
            print('clicked')
            return redirect(url_for('editplan'))
        
        if request.method == 'POST' and 'delete' in request.form:
            print('clicked')
            cursor = mysql.connection.cursor(pymysql.cursors.DictCursor)
            print(session['id'])
            cursor.callproc("removeUser", args = (session['id'],))
            mysql.connection.commit()
            return redirect(url_for('logout'))
        
        cursor = mysql.connection.cursor(pymysql.cursors.DictCursor)
        cursor.callproc('getUserInformation', args = (session['id'],))
        userInfo = cursor.fetchone()
        cursor.callproc('getPaymentInformation', (userInfo['planId'],))
        paymentInfo = cursor.fetchone()
        print(paymentInfo)
        print(userInfo)
        dateStr = str(userInfo['planDate'].month) + '/' + str(userInfo['planDate'].day) + '/' + str(userInfo['planDate'].year)
        return render_template('profile.html', userinfo=userInfo, paymentinfo = paymentInfo, datestr = dateStr)
        
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))


@app.route('/editplan', methods=['GET', 'POST'])
def editplan():
    paymentPlans = []
    # Check if user is loggedin
    if 'loggedin' in session:
        #Get payment plans
        cursor = mysql.connection.cursor(pymysql.cursors.DictCursor)
        cursor.execute('call getPaymentPlans()')
        paymentPlans = cursor.fetchall()

        if request.method == 'POST' and 'plan' in request.form:
            plan = request.form['plan']
            print('test', plan)
            # Call process to change payment plan
            cursor = mysql.connection.cursor(pymysql.cursors.DictCursor)
            cursor.execute('call editPaymentPlan(%s, %s)', (session['id'], plan))
            mysql.connection.commit()
            # Redirect to profile page
            return redirect(url_for('profile'))
        
        return render_template('editplan.html', plans = paymentPlans)
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))


"""

New Playlist Page

"""
@app.route('/newplaylist', methods=['GET', 'POST'])
def newplaylist():
    status = ['Public', 'Private']
    # Check if user is loggedin
    if 'loggedin' in session:
        if request.method == 'POST' and 'name' in request.form:
            name = request.form['name']
            status = request.form['status']
            print('MY USER', session['id'])
            cursor = mysql.connection.cursor(pymysql.cursors.DictCursor)
            cursor.execute('CALL createPlaylist(%s, %s, %s)',
                           (name, status, int(session['id'])))
            mysql.connection.commit()
             # Redirect to home page
            return redirect(url_for('home'))
        return render_template('newplaylist.html', username=session['email'], status = status)
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))


"""

Edit Playlist Page

"""
@app.route('/editplaylist/<playlist_id>', methods=['GET', 'POST'])
def editplaylist(playlist_id):
    status = ['Public', 'Private']
    # Check if user is loggedin
    if 'loggedin' in session:
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT getPlaylistName(%s)', (playlist_id))
        playlistname = cursor.fetchone()[0]

        if request.method == 'POST' and 'name' in request.form:
            name = request.form['name']
            status = request.form['status']
            print('MY USER', session['id'])
            cursor = mysql.connection.cursor(pymysql.cursors.DictCursor)
            cursor.callproc('editPlaylist', (name, status, playlist_id))
            mysql.connection.commit()
             # Redirect to home page
            return redirect(url_for('playlist', playlist_id = playlist_id))
        return render_template('editplaylist.html', status = status, name = playlistname)
    # User is not loggedin redirect to login page
    return redirect(url_for('login'))


"""

Playlist Page

"""
@app.route('/playlist/<playlist_id>', methods=['GET', 'POST'])
def playlist(playlist_id):
    if 'loggedin' in session:
        print(request.form)

        if request.method == 'POST' and 'delete' in request.form:
            cursor = mysql.connection.cursor(pymysql.cursors.DictCursor)
            song_id = request.form['delete']
            cursor = mysql.connection.cursor()
            cursor.execute('CALL removeSongFromPlaylist(%s, %s)',
                           (playlist_id, song_id))
            mysql.connection.commit()
        
        if request.method == 'POST' and 'edit' in request.form:
            return redirect(url_for('editplaylist', playlist_id=playlist_id))

        cursor = mysql.connection.cursor()
        cursor.execute('SELECT getPlaylistName(%s)', (playlist_id))
        playlistname = cursor.fetchone()[0]

        cursor = mysql.connection.cursor(pymysql.cursors.DictCursor)
        cursor.execute('CALL getPlaylistSongs(%s)', (playlist_id))
        playlistsongs = list(cursor.fetchall())

        return render_template('playlist.html', songs = songs, playlistsongs = playlistsongs, 
                playlistId = playlist_id, name = playlistname)
    return redirect(url_for('login'))

"""

Songs Page

"""
@app.route('/songs/<playlist_id>', methods=['GET', 'POST'])
def songs(playlist_id):
    if 'loggedin' in session:
        print(request.form)
        if request.method == 'POST' and 'add' in request.form:
            cursor = mysql.connection.cursor(pymysql.cursors.DictCursor)
            song_id = request.form['add']
            cursor.execute('CALL addSongPlaylistLink(%s, %s)',
                           (playlist_id, song_id))
            mysql.connection.commit()
        
        cursor = mysql.connection.cursor(pymysql.cursors.DictCursor)
        cursor.execute('CALL getSongsForPlaylistView(%s)', (playlist_id))
        songs = list(cursor.fetchall())    

        return render_template('songs.html', songs = songs, playlistId = playlist_id)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)
