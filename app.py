from flask import Flask, render_template
app=Flask(__name__,template_folder='template')

@app.route('/')
def hello():
    return render_template('hello.html')  

    