# PyMySQL is a pure-Python MySQL driver. This line lets Django's MySQL
# backend use it in place of mysqlclient (no C compiler needed).
import pymysql

pymysql.install_as_MySQLdb()
