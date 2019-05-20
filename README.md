# Skills Extractor

Extract skills set which document provide:

1. Upload document for storage and searching
1. Extract skills from each document. It may help you have a quick preview before reading.

## How it work
Simple web application using the Python 3, [Flask](http://flask.pocoo.org), SQLAlchemy.  
After register, you can upload document for storage and searching.  
Document is indexed using [Elasticsearch](https://www.elastic.co).  
[RDFLib](https://github.com/RDFLib/rdflib) load all defined skills in ontology resource files, and report matching skills on document. 

## Quick Start

### Create an environment

Go to the project folder and create a venv folder within:

```sh
$ cd myproject
$ python3 -m venv venv
```

Activate the environment:

```sh
$ . venv/bin/activate
```

On Windows:

```sh
$ venv\Scripts\activate
```

Your shell prompt will change to show the name of the activated environment.


### Review the set up guides to configure the app:

1. [setup-with-docker.md](setup-with-docker.md)
1. [setup-without-docker.md](setup-without-docker.md)
