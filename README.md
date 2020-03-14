# thorn
Authentication module for Lemonade Project

### Install
```
git clone git@github.com:eubr-bigsea/thorn.git
cd thorn
pip install -r requirements.txt
```

### Config
Copy `thorn.yaml.example` to `thorn.yaml`
```
cp thorn.yaml.example thorn.yaml
```

Create a database named `thorn` in a MySQL server and grant permissions to a user.
```
#Example
mysql -uroot -pmysecret -e "CREATE DATABASE thorn;"
```

Edit `thorn.yaml` according to your database config
```
thorn:
    debug: true
    environment: prod
    port: 3319
    secret: 123456
    providers:
    - thorn
    - ldap
    servers:
        database_url: mysql+pymysql://user:secret@server:3306/thorn
        ldap: ldap://server
    services:
    config:
        SQLALCHEMY_POOL_SIZE: 0
        SQLALCHEMY_POOL_RECYCLE: 60
```
### Create tables in the database
THORN_CONFIG=thorn.yaml PYTHONPATH=. python thorn/manage.py upgrade

### Run
```
THORN_CONFIG=thorn.yaml PYTHONPATH=. python thorn/app.py
```

#### Using docker
Build the container
```
docker build -t bigsea/thorn .
```

Repeat [config](#config) stop and run using config file
```
docker run \
  -v $PWD/thorn.yaml:/usr/src/app/thorn.yaml \
  -p 3319:3319 \
  bigsea/thorn
```
