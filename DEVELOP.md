# Develop Cactus

## Run tests

### Create virtualenv

```console
$ virtualenv env
$ source env/bin/activate
```

### Install requirements

```console
$ ./env/bin/python install -r requirements.txt
$ ./env/bin/python install -r test_requirements.txt
```

### Run Nose tests

```console
$ ./env/bin/python setup.py install && ./env/bin/python setup.py nosetests
```

