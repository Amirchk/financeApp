#////////////////////////////////////
### IMPORT LIBRARIES ###
#////////////////////////////////////
from flask import Flask, render_template,request,session,url_for,redirect
import json 
import re
import mysql.connector
from datetime import datetime
app = Flask(__name__)
app.secret_key = "MySecretKey"


#////////////////////////////////////
### Zillow Api Global code ###
#////////////////////////////////////
import requests

url = "https://zillow-com1.p.rapidapi.com/property"


headers = {
	"X-RapidAPI-Key": "10d9e6ae41msh1f9758494c52cf6p10886cjsnb835fdedaa0e",
	"X-RapidAPI-Host": "zillow-com1.p.rapidapi.com"
}



#////////////////////////////////////
### MYSQL DATABASE ###
#////////////////////////////////////
mydb = mysql.connector.connect(
  host="localhost",
  user="root",
  password="Qwerty",
  database="transaction"
)
mycursor = mydb.cursor(buffered=True)

#///////////////////////////
#     ATHENTICATION CODE below
#///////////////////////////

#------REGISTERATION PAGE
@app.route("/register",methods=['GET','POST'])
def register():
    msg=''
    if request.method == 'POST'and 'userId' in request.form and 'pass' in request.form and 'email' in request.form:
        detail = request.form
        userId = detail['userId']
        email = detail['email']
        password = detail['pass']
        # Check if account exists using MySQL
        mycursor.execute('SELECT * FROM register WHERE userId = %s', (userId,))
        account = mycursor.fetchone()
        # If account exists show error and validation checks
        if account:
            msg = 'Account already exists! Go to `<a>login Page` '
        elif not re.match(r'[^@]+@[^@]+\.[^@]+', email):
            msg = 'Invalid email address!'
        elif not re.match(r'[A-Za-z0-9]+', userId):
            msg = 'Username must contain only characters and numbers!'
        elif not userId or not password or not email:
            msg = 'Please fill out the form!'
        else:
            # Account doesnt exists and the form data is valid, now insert new account into accounts table
            mycursor.execute('INSERT INTO register VALUES (%s, %s, %s)', (userId, email, password ))
            mydb.commit()
            msg = 'You have successfully registered!'

    elif request.method == 'POST':
        # Form is empty... (no POST data)
        msg = 'Please fill out the form!'
    
    return render_template('./register.html',msg=msg)

#---------LOGIN PAGE
@app.route("/login",methods=['GET','POST'])
def login():
    msg=''
    if request.method == 'POST' and 'email' in request.form and 'pass' in request.form:
        detail = request.form
        email = detail['email']
        password = detail['pass']
        #------SQL QUERIES
        mycursor.execute('SELECT * FROM register WHERE email = %s AND password = %s', (email, password,))
        # Fetch one record and return result
        account = mycursor.fetchone()

        # If account exists in accounts table in our database
        if account:
            # Create session data, we can access this data in other routes
            session['loggedin'] = True
            session['userId'] = account[0]
            session['email'] = account[1]
            
            # Redirect to home page
            return redirect('/')
        else:
            # Account doesnt exist or username/password incorrect
            msg = 'Incorrect username/password! or register Yourself'
        
    return render_template('./login.html',msg=msg)
#logout page
@app.route("/logout")
def logout():
    # Remove session data, this will log the user out
   session.pop('loggedin', None)
   session.pop(0, None)
   session.pop(1, None)
   # Redirect to login page
   return redirect(url_for('login'))


#////////////////////////////////////
### Website page ROUTES ###
#////////////////////////////////////
#------HOME PAGE
@app.route("/")
def home():
    Data=[] # this will hold username and Cash data
    # Check if user is loggedin
    if 'loggedin' in session:
        # User is loggedin show them the home page
        mycursor.execute('select addCash from cash where userId = %s',(session['userId'],))
        mydb.commit()
        amount = mycursor.fetchone()
        username = session['userId']
        #check whether user has amount in his account or not
        if amount == None:
            print("amount is zero")
            amount=0
        Data = [amount,username] # get the last updated price data from SQL Cash table
        
        ####-----SQL Queries
        sql = 'select address,state,zipcode,price,time from transaction where user_id=%s'
        mycursor.execute(sql,(session['userId'],))
        indexData = mycursor.fetchall() ### fetched data from trnasaction table
        
        #get total price of properties
        sql = 'select sum(price) from transaction where user_id=%s'
        mycursor.execute(sql,(session['userId'],))
        totalval = mycursor.fetchone()
        return render_template('index.html',Data = Data, indexData=indexData,totalval=totalval)

    # User is not loggedin redirect to login page
    return redirect(url_for('login'))


#---------=======BUY PAGE
@app.route("/buy",methods=['POST','GET'])
def buy():
    if 'loggedin' in session:
        msg=''
        detail = request.form #it has data of all input fields
        if request.method=='POST':
            #required data for transaction table
            quotePrice = detail['quotePrice']
            address = detail['Address']
            zipCode = detail['zipcode']

            ##-------API REQUEST using zpid and get price
            querystring = {"zpid":zipCode}
            response = requests.request("GET", url, headers=headers, params=querystring)
            pData=response.json()

            now = datetime.now()
            Time = now.strftime('%Y-%m-%d %H:%M:%S')# inserting time in sql db
            userId = session['userId'] # loggedIn user
            state = pData['state'] #data requesting zillow api.
            Type= 'buy'

            ##==========Check that user can buy a property or not-----
            getUser = 'select addCash from cash where userId=%s'
            val = (session['userId'],)
            mycursor.execute(getUser,val)
            UserAmount = mycursor.fetchone()
            cashOutput = 0
            if UserAmount is not None:
                for x in UserAmount:
                    cashOutput = int(x) - int(quotePrice)
                
                if cashOutput >= 0:
                    ## ------Updating a cash Table reduce cash if property is bought
                    cashupdatesql = 'update cash set addCash = (addCash - %s) where userId=%s'
                    cashval = (quotePrice,session['userId'],)
                    mycursor.execute(cashupdatesql,cashval)
                    mydb.commit()

                    #------SQL QUERIES
                    sql = "INSERT INTO transaction (user_id,address,state,zipcode,price,type,time) VALUES (%s,%s,%s, %s,%s,%s,%s)"
                    val = (userId,address,state, zipCode, quotePrice,Type,Time)
                    mycursor.execute(sql, val)
                    mydb.commit()
                    msg="Congratulation!! you have bought a property"
                else:
                    msg = "You dont have enough cash to buy property"
            else:
                msg = "Please enter money in your account from AddCash Page"
        
        #------SQL QUERY to bring Zpid data for drop down menu
        sql = "select * from quotetable"
        mycursor.execute(sql)
        zipdata = mycursor.fetchall()
        for z in zipdata:
            for y in z:
                print(y)
        if zipdata:
            return render_template('./buy.html',msg=msg,zipdata=zipdata)
        return render_template('./buy.html')
    else:
        return redirect(url_for('login'))

#--------SELL PAGE
@app.route("/sell",methods=['GET','POST'])
def sell():
    
    if 'loggedin' in session:
        sellData=[]
        Type = 'sell'
        userId = session['userId']
        
        now = datetime.now()
        Time = now.strftime('%Y-%m-%d %H:%M:%S')# inserting time in sql db
        
        #---bring address data from transaction table and show it on sell page
        sql = 'select address,zipcode,price from transaction where type="buy" and user_id=%s '
        mycursor.execute(sql,(session['userId'],))
        fdata = mycursor.fetchall() 
        
        if request.method == 'POST' and 'addressSelect' in request.form:
            address = request.form['addressSelect']
            zipCode = request.form.get('ZCodeSelect')
            quotePrice = request.form.get('priceSelect')
            ##-------API REQUEST using zpid and get price
            querystring = {"zpid":zipCode}
            response = requests.request("GET", url, headers=headers, params=querystring)
            resData = response.json()
            state = resData['state']
            #======if property is sold then add money to Cash ====
            profitQuery = 'update cash set addCash = (addCash + %s) where userId = %s'
            profitVal = (quotePrice,session['userId'],)
            mycursor.execute(profitQuery,profitVal)
            mydb.commit() # commit the current transaction

            ####------SQL QUERIES
            sql = "INSERT INTO transaction (user_id,address,state,zipcode,price,type,time) VALUES (%s,%s,%s, %s,%s,%s,%s)"
            val = (userId,address,state, zipCode, quotePrice,Type,Time)
            mycursor.execute(sql, val)
            mydb.commit()
        else:
            return render_template('./sell.html',sellData=fdata)
        
        return render_template('./sell.html',sellData=fdata)
    else:
        return redirect(url_for('login'))

#-------QUOTE PAGE
@app.route("/quote",methods=['POST','GET'] )
def quote():
    if 'loggedin' in session:
        msg=''
        if request.method == 'POST' and 'Address' in request.form and 'ZipCode' in request.form:
            address = request.form['Address']
            zipcode= request.form['ZipCode']
            session['zipcode'] = zipcode
            session['address']= address
            if address != '' and zipcode != '':
                sql = "select * from quotetable where quoteid=%s"
                val = (zipcode,)
                mycursor.execute(sql, val)
                zipdata = mycursor.fetchone()
                if zipdata:
                    msg = "Zpid is already exist in your data go to buy section"
                    return render_template('./quote.html',msg=msg)
                else:
                    sql = "INSERT INTO quotetable (quoteid) VALUES (%s)"
                    val = (zipcode,)
                    mycursor.execute(sql, val)
                    mydb.commit()
                    return redirect(url_for('quote'))
            
        return render_template('./quote.html',msg=msg)
    else:
        return redirect(url_for('login'))


#-------QUOTED PAGE
@app.route("/quoted",methods=['POST','GET'] )
def quoted():
    if 'loggedin' in session:
        quotedData = dict()
        address = session['address']
        zipcode = session['zipcode']
        ##-------API REQUEST using zpid and get price
        querystring = {"zpid":zipcode}
        response = requests.request("GET", url, headers=headers, params=querystring)
        # print(response.text[38])
        pData=response.json()

        #-===---append data in list 
        quotedData['address'] = address
        quotedData['price'] = pData['price']

        return render_template('./quoted.html',quotedData = quotedData)
    else:
        return redirect(url_for('login'))

#-----------HISTORY PAGE
@app.route("/history",methods=['GET','POST'])
def history():
    if 'loggedin' in session:
        sql = 'select address,state,zipcode,price,type,time from transaction where user_id=%s'
        mycursor.execute(sql,(session['userId'],))
        d=mycursor.fetchall()### fetched data from trnasaction table

        for x in d:
            print( list(x) )
        
        # mycursor.execute()
        return render_template('./history.html',history=d)
    else:
        return redirect(url_for('login'))


#-----ADDCASH PAGE
@app.route("/add",methods=['GET','POST'])
def add():
    if 'loggedin' in session:
        msg=''
        if request.method == 'POST' and 'AddCash' in request.form:
            detail = request.form
            cash = detail.get('AddCash')
            getUser = 'select userId from cash where userId=%s'
            val = (session['userId'],)
            mycursor.execute(getUser,val)
            existUser = mycursor.fetchone()
            print(existUser)
            if not existUser:
                sql = "INSERT INTO cash (userId,addCash) VALUES (%s,%s)"
                vals = (session['userId'],cash,)
                mycursor.execute(sql,vals)
                mydb.commit()
            #-------------------below sql query will check that loggedIn user has cash or zero cash 
            elif not cash:
                sql = "INSERT INTO cash (userId,addCash) VALUES (%s,%s)"
                vals = (session['userId'],cash,)
                mycursor.execute(sql,vals)
                mydb.commit()
            else:
                #---------update if cash has some value
                updatesql='update cash SET addCash = addCash + %s where userId=%s'
                mycursor.execute(updatesql,(cash,session['userId'],))
                mydb.commit()
        return render_template('./add.html')
    else:
        return redirect(url_for('login'))

#////////////////////////////////////
### MAIN APPLICATION ###
#////////////////////////////////////
if __name__ == '__main__':
   app.run()