# project/server/extractor/ontologies.py

import os
from os import listdir
from os.path import isfile, join

import rdflib
from rdflib.namespace import OWL, RDF, RDFS, ClosedNamespace
from rdflib import URIRef, Graph

from typing import Iterable, Set

skill_nodes_cache = None


class OntNode:

    def __init__(self, namespace_uri, name, type="NamedIndividual", labels: Iterable[str]=None, parents: Iterable[str]=None,
                 difficulty: int = 0, keyword_only: bool = False):
        self.namespace_uri = namespace_uri
        self.name = name
        self.labels = labels
        self.type = type
        self.parents = parents
        self.difficulty = difficulty
        self.keyword_only = keyword_only

    def __repr__(self):
        if (len(self.labels) > 0):
            return "{} ({})".format(self.name, ", ".join(self.labels))
        else:
            return self.name


def load_skill_nodes_from_rdf_resources(skills_resource_dir) -> Set[OntNode]:
    """
    Load skills in rdf format from resource directory and return as list node
    """

    global skill_nodes_cache
    if skill_nodes_cache is not None:
        return skill_nodes_cache

    ont_files = []
    for f in listdir(skills_resource_dir):
        f_path = join(skills_resource_dir, f)
        if isfile(f_path) and f_path.endswith(".ttl"):
            ont_files.append(f_path)

    if len(ont_files) == 0:
        print("Ontology (.ttl) files is not found")
        return set()

    print('Load ontology files: {}'.format(ont_files))

    skills = set()
    for ont_file in ont_files:
        try:
            graph = rdflib.Graph()
            graph.parse(ont_file, format="ttl")

            base_namespace_uri = get_namespace_uri(
                g=graph, namespace_prefix=None)

            triples = graph.triples((None, RDF.type, None))
            for s, p, o in triples:
                if not (o == OWL.NamedIndividual) and not (o == OWL.Class):
                    continue

                subject = split_triple(s)
                object = split_triple(o)
                ontNode = OntNode(subject[0], subject[1], type=object[0])
                skills.add(ontNode)

                # Labels if exists
                triples_labels = graph.triples((s, RDFS.label, None))
                labels = [split_triple(o2)[1] for s2, p2, o2 in triples_labels]
                ontNode.labels = labels

                # Parents
                if o == OWL.NamedIndividual:
                    triples_parents = graph.triples((s, RDF.type, None))
                    parents = [split_triple(
                        o2)[1] for s2, p2, o2 in triples_parents if o2 != OWL.NamedIndividual]
                    ontNode.parents = parents
                else:
                    o_parents = graph.transitive_objects(
                        subject=s, property=RDFS.subClassOf)
                    parents = [split_triple(o2)[1] for o2 in o_parents if split_triple(o2)[
                        1] != ontNode.name]
                    ontNode.parents = parents

                # Custom properties
                RDF_SKILL_PROPERTY = ClosedNamespace(
                    uri=URIRef(str(base_namespace_uri)),
                    terms=[
                        "difficulty", "keywordOnly"]
                )

                triples_difficulty = graph.triples(
                    (s, RDF_SKILL_PROPERTY.difficulty, None))
                for s2, p2, o2 in triples_difficulty:
                    try:
                        ontNode.difficulty = int(o2)
                    except ValueError:
                        print("difficulty {} of {} not an int!".format(
                            o2, ontNode.name))

                triples_keyword_only = graph.triples(
                    (s, RDF_SKILL_PROPERTY.keywordOnly, None))
                for s2, p2, o2 in triples_keyword_only:
                    try:
                        ontNode.keyword_only = bool(o2)
                    except ValueError:
                        print("o_keyword_only {} of {} not an bool!".format(
                            o2, ontNode.name))
        except BaseException:
            print("Parse file {} exception".format(ont_file))
            raise

    # #print skills
    # skills_str = []
    # for ontNode in skills:
    #     skill = "{} (labels: {}, parents: {}".format(ontNode.name, ontNode.labels, ontNode.parents)
    #     if ontNode.keyword_only is True:
    #         skill += ", keywordOnly: " + str(ontNode.keyword_only)
    #     if ontNode.difficulty:
    #         skill += ", difficulty: " + str(ontNode.difficulty)
    #     skills_str.append(skill)
    # print("Skills: {}".format("\n   ".join(skills_str)))

    skill_nodes_cache = skills
    return skills


def get_namespace_uri(g: Graph, namespace_prefix):
    for ns in g.namespace_manager.namespaces():
        urlref = ns[1]
        if namespace_prefix == ns[0] and isinstance(urlref, URIRef):
            uri = super(URIRef, urlref).__repr__()
            return uri

    return None


def split_triple(triple):
    """
    Split a triple to array which first item is uri, second is name
    """

    if triple is None:
        return [None, None]

    triple_str = str(triple)
    if triple_str.startswith("http://"):
        triple_str = triple_str.split("#")
        if len(triple_str) > 1:
            uri = triple_str[0]
            name = triple_str[1]
            return [uri, name]
        else:
            name = triple_str[0]
        return [None, name]
    else:
        name = triple_str
        return [None, name]


if __name__ == "__main__":
    skills_resource_dir = "/Users/thanhphan/Documents/Data/research/python/skills_extractor/project/server/resources/ontologies/"
    load_skill_nodes_from_rdf_resources(skills_resource_dir)
