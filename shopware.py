#!/usr/bin/env python3

import json, urllib3, uuid


class HTTPResponseException(Exception):
    def __init__(self, message, status_code):
        super().__init__(message)

        self.status_code = status_code


class ApiClient:
    def __init__(self, base_url, key_id, key_secret, httpClientOptions={}):
        self.base_url = base_url
        self.httpClient = urllib3.PoolManager(**httpClientOptions)
        self.key_id = key_id
        self.key_secret = key_secret
        self.bearer_token = self._get_access_token()

    def call(self, endpoint, fields=None, data=None, headers=None):
        auth_headers = {
            "Authorization": f"Bearer {self.bearer_token}",
            "Content-Type": "application/json",
            "Accept": "application/vnd.api+json",
        }

        if headers is not None:
            # TODO: The correct case is assumed?! Document?!
            auth_headers.update(headers)

        try:
            return self.unauthenticated_call(
                endpoint, fields=fields, data=data, headers=auth_headers
            )
        except HTTPResponseException as e:
            # Redo request if status is 401 with new token
            if e.status_code == 401:
                self._refresh_token()
                auth_headers["Authorization"] = f"Bearer {self.bearer_token}"
                return self.unauthenticated_call(
                    endpoint, fields=fields, data=data, headers=auth_headers
                )

            raise e

    def unauthenticated_call(self, endpoint, fields=None, data=None, headers=None):
        api_args = {}
        if fields is not None:
            api_args["fields"] = fields
            method = "POST"
        elif data is not None:
            api_args["body"] = json.dumps(data).encode("utf-8")
            method = "POST"
        else:
            method = "GET"

        if headers is not None:
            api_args["headers"] = headers

        if endpoint[:4] == "http":
            url = endpoint
        else:
            url = f"{self.base_url}/api/{endpoint}"

        r = self.httpClient.request(method, url, **api_args)

        if r.status < 200 or r.status >= 300:
            raise HTTPResponseException(r.data.decode("utf-8"), r.status)

        try:
            return json.loads(r.data.decode("utf-8"))
        except:
            print(r.data.decode("utf-8"))

    def sync_call(self, data, headers={}, indexing=None):
        if indexing and indexing in ["use-queue-indexing", "disable-indexing"]:
            headers["indexing-behavior"] = indexing

        return self.call("_action/sync", data=data, headers=headers)

    def _refresh_token(self):
        print("Refreshing Token")
        # TODO: Implement refresh token if not user/password is used
        self.bearer_token = self._get_access_token()

    def _get_access_token(self):
        token_response = self.unauthenticated_call(
            "oauth/token",
            fields={
                "grant_type": "client_credentials",
                "client_id": self.key_id,
                "client_secret": self.key_secret,
            },
        )

        return token_response["access_token"]


def generate_uuid():
    return str(uuid.uuid4()).replace("-", "")


def group_api_included(included):
    grouped = {}

    for i in included:
        if i["type"] not in grouped.keys():
            grouped[i["type"]] = {}

        grouped[i["type"]][i["id"]] = i

    return grouped


def parse_single_entity(relation, data):
    relation_type = relation["type"]

    parsed = {"id": relation["id"]}
    if relation_type in data.keys() and relation["id"] in data[relation_type].keys():
        parsed.update(data[relation_type][relation["id"]]["attributes"])

    parsed.update(
        parse_relationships(data[relation_type][relation["id"]]["relationships"], data)
    )

    return parsed


def parse_relationships(relationships, data):
    result = {}

    for relationship_name, relation in relationships.items():
        if not relation["data"]:
            continue

        if isinstance(relation["data"], dict):
            parsed = parse_single_entity(relation["data"], data)

            if parsed:
                result[relationship_name] = parsed

        elif isinstance(relation["data"], list):
            result[relationship_name] = []

            for rel in relation["data"]:
                parsed = parse_single_entity(rel, data)
                if parsed:
                    result[relationship_name].append(parsed)
        else:
            raise Exception(f"Do not know how to parse {type(relation['data'])}")

    return result


def parse_api_response(response):
    additional_data = group_api_included(response["included"])

    result = []
    for row in response["data"]:
        row_parsed = row["attributes"]
        row_parsed["id"] = row["id"]

        row_parsed.update(parse_relationships(row["relationships"], additional_data))

        result.append(row_parsed)

    return result


def get_sync_chunks(data, chunk_size):
    for i in range(0, len(data), chunk_size):
        yield data[i : i + chunk_size]
