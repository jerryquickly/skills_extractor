import os
import json
import re
from typing import List

import PyPDF2
from flask import current_app as app
from elasticsearch import Elasticsearch
from project.server.extractor.ontologies import load_skill_nodes_from_rdf_resources

class SkillExtract(object):
    def __init__(self, name, match_str, n_match):
        self.name = name
        self.match_str = match_str
        self.n_match = n_match


def extract_skills_in_document(document_id) -> List[SkillExtract]:
    """
    Extract skill in a document and return founded skills.
    - **return**::
        :return: List of SkillExtract or empty
    """

    skills_resource_dir = os.path.join(app.root_path, "resources/ontologies")
    skill_nodes = load_skill_nodes_from_rdf_resources(skills_resource_dir)

    if len(skill_nodes) == 0:
        print("There is no skill to query")
        return []

    result = set()
    es_index = app.config["ELASTICSEARCH_INDEX"]

    skill_nodes = list(skill_nodes) #set to list
    skill_nodes_len = len(skill_nodes)
    skill_nodes_dict = dict() #dict by skill name/label to skill_node
    for skill_node in skill_nodes:
        skill_nodes_dict[skill_node.name] = skill_node
        if skill_node.labels is not None:
            for label in skill_node.labels:
                skill_nodes_dict[label] = skill_node

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
            content_lower = doc['_source']['content'].lower()

            for skill in skills_page:
                skill_node = skill_nodes_dict.get(skill)
                regex = re.compile(r"\b{}\b".format(re.escape(skill.lower())))
                n_match = len(regex.findall(content_lower))
                if n_match > 0:
                    if skill_node is not None and skill_node.type == "NamedIndividual":
                        skill_extracts = [SkillExtract(
                            name=parent, match_str=skill, n_match=n_match) for parent in skill_node.parents]
                        result.update(skill_extracts)
                    else:
                        skill_extract = SkillExtract(name=skill, match_str=skill, n_match=n_match)
                        result.add(skill_extract)

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
