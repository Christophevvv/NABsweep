NABsweep requires python2 and python3 because the sweep logic as well as django requires python3 and NAB requires python2.

To install all requirements run the setup.sh script.
If you want to run the MySQL server on the same hosts, the following requirements should be installed:

- apt install mysql-server libmysqlclient-dev

Next 'sudo mysql' and add the following user to the server:

" GRANT ALL PRIVILEGES ON *.* TO 'nabsweep'@'localhost' IDENTIFIED BY 'nabsweep'; "

You can change the credentials, however make sure to also change them in the django settings.py file.

" CREATE DATABASE NABsweep; "

you can now quit the mysql cli and create all the tables with django:

python3 manage.py migrate

---
