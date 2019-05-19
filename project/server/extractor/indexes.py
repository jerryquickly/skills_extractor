import os
import json
from typing import List

import PyPDF2
from elasticsearch import Elasticsearch
from project.server.extractor.ontologies import load_skill_nodes_from_rdf_resources


def extract_skills_in_document(document_id) -> List[str]:
    """
    Extract skill in a document and return founded skills
    """

    skills_resource_dir = "/Users/thanhphan/Documents/Data/research/python/skills_extractor/project/server/resources/ontologies/"
    skill_nodes = load_skill_nodes_from_rdf_resources(skills_resource_dir)

    if len(skill_nodes) == 0:
        print("There is no skill to query")
        return []

    result = []
    es_index = "prod-index"  # app.config["ELASTICSEARCH_INDEX"]

    skill_nodes = list(skill_nodes) #set to list
    skill_nodes_len = len(skill_nodes)

    page_index = 0
    page_size = 100

    while page_size * page_index < skill_nodes_len:
        page_from = page_index * page_size
        page_to = page_index * page_size + page_size
        page_to = min(page_to, skill_nodes_len)
        page_index = page_index + 1

        skill_nodes_page = skill_nodes[page_from:page_to]
        skills_page = []
        for skill_node in skill_nodes_page:
            skills_page.append(skill_node.name)
            skills_page.extend(skill_node.labels)

        res = search_skills(skills_page, index=es_index,
                            document_ids=[document_id])

        for doc in res['hits']['hits']:
            for skill in skills_page:
                if exists_skill(skill, doc['_id']):
                    result.append(skill)

    print("Extract {} skills on document id {}. Skills: {}".format(
        len(result), document_id, result))
    return result


def search_skills(skills: List[str], index="prod-index", doc_type="document", default_field="content",
                  document_ids: List=None):
    es = Elasticsearch()

    strs_quoted = []
    # quotes for query exactly word
    for i in range(0, len(skills)):
        str_quoted = skills[i].translate(str.maketrans('"', '\"'))
        str_quoted = "\"{}\"".format(str_quoted)
        strs_quoted.append(str_quoted)

    res = es.search(index=index, body={
        "query": {
            "bool": {
                "must": [
                    {"terms": {"id": document_ids}},
                    {"query_string": {
                        "default_field": "content",
                        "query": " OR ".join(strs_quoted)
                    }}
                ],
                "filter": [
                    {"term":  {"_type": doc_type}}
                ]
            }
        }
    })

    return res


def exists_skill(skill: str, document_id, index="prod-index", doc_type="document", default_field="content") -> bool:
    es = Elasticsearch()

    # quotes for query exactly word
    str_quoted = skill.translate(str.maketrans('"', '\"'))
    str_quoted = "\"{}\"".format(str_quoted)

    res = es.count(index=index, body={
        "query": {
            "bool": {
                "must": [
                    {"query_string": {
                        "default_field": "content",
                        "query": str_quoted
                    }}
                ],
                "filter": [
                    {"term":  {"id": document_id}}
                ]
            }
        }
    })

    return int(res["count"]) > 0

    
if __name__ == "__main__":
    extract_skills_in_document(65)
