@ECHO OFF
:: This script does two things. It first opens a *new* cmd prompt to run the client.
:: It then runs the server inside the *original* cmd prompt. 
:: Because the server needs to be up and running before a client can connect,
:: there is a 10 second delay on the execution of the client.
:: %cd% = current directory

start cmd /k "TIMEOUT 10 && python %cd%\python\kuatroKinectClientv2PYTHON.py"
jython -i %cd%\python\kinectineBegin.py
