#!/usr/bin/env python3

import kubernetes
from kubernetes.client.rest import ApiException

import threading
import logging
import os

FORMAT = "[%(filename)s:%(lineno)s - %(funcName)20s() ] %(message)s"
logging.basicConfig(format=FORMAT)

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)


class WatchedSecret:
    def __init__(self, name, namespace):
        self.name = name
        self.namespace = namespace

    def namespace_valid(self, namespace):
        return True


def safe_label_get(obj, label_name, default=None):
    if obj.metadata.labels is None:
        return default
    else:
        return obj.metadata.labels.get(label_name, default)


def safe_annotation_get(obj, annotation_name, default=None):
    if obj.metadata.annotations is None:
        return default
    else:
        return obj.metadata.annotations.get(annotation_name, default)


class Replicator:
    def __init__(self, namespace):
        kubernetes.config.load_incluster_config()
        self.lock = threading.Lock()
        self.watched_secrets = {}

        self.namespace = namespace

        self.label_names = os.environ.get('SECRET_REPLICATOR_LABEL_NAMES',
                                          'secret-replicator.daewok/replicate').split(';')
        self.managed_annotation_name = os.environ.get('SECRET_REPLICATOR_MANGED_ANNOTATION_NAME',
                                                      'secret-replicator.daewok/managed')

    def add_secret_to_namespace(self, s, raw_secret, ns, v1):

        try:
            existing_secret = v1.read_namespaced_secret(s.name, ns)
        except ApiException as e:
            if e.status == 404:
                existing_secret = None
            else:
                raise e

        if existing_secret is None:
            log.info('Creating secret %s/%s', ns, s.name)
            raw_secret.metadata.resource_version = None
            v1.create_namespaced_secret(ns, raw_secret)
        elif safe_annotation_get(existing_secret, self.managed_annotation_name) == 'true':
            log.info('Replacing secret %s/%s', ns, s.name)
            raw_secret.metadata.resource_version = existing_secret.metadata.resource_version
            v1.replace_namespaced_secret(s.name, ns, raw_secret)
        else:
            log.warn('Secret %s/%s already exists and is not managed by secret replicator',
                     ns, s.name)

    def add_secret_to_matching_namespaces(self, s, v1, target_namespaces=None):
        raw_secret = v1.read_namespaced_secret(s.name, s.namespace,
                                               export=True,
                                               exact=False)

        if raw_secret.metadata.annotations is None:
            raw_secret.metadata.annotations = {}

        raw_secret.metadata.annotations[self.managed_annotation_name] = "true"

        if target_namespaces is None:
            all_ns_objs = v1.list_namespace(watch=False).items
            target_namespaces = [x.metadata.name for x in all_ns_objs]

        for ns_name in target_namespaces:
            if s.namespace_valid(ns_name):
                self.add_secret_to_namespace(s, raw_secret, ns_name, v1)

    def watch_for_new_namespaces(self):
        v1 = kubernetes.client.CoreV1Api()
        w = kubernetes.watch.Watch()

        for e in w.stream(v1.list_namespace):
            type = e['type']
            obj = e['object']

            log.debug('got %s event', type)
            log.debug('got %s object', obj)

            if type == 'ADDED':
                with self.lock:
                    log.info('Adding secrets to new namespace: %s', obj.metadata.name)
                    for s in self.watched_secrets.values():
                        self.add_secret_to_matching_namespaces(s, v1, target_namespaces=[obj.metadata.name])

    def secret_should_be_replicated(self, s):
        if safe_annotation_get(s, self.managed_annotation_name) is not None:
            return False

        for label_name in self.label_names:
            if safe_label_get(s, label_name) is not None:
                return True

        return False

    def watch_for_new_secrets(self):
        v1 = kubernetes.client.CoreV1Api()
        w = kubernetes.watch.Watch()

        ns = self.namespace

        for e in w.stream(v1.list_namespaced_secret, namespace=ns):
            with self.lock:
                type = e['type']
                obj = e['object']

                log.debug('got %s event', type)
                log.debug('got %s object', obj)

                has_label = self.secret_should_be_replicated(obj)

                secret_name = obj.metadata.name
                secret_ns = obj.metadata.namespace

                if type == 'ADDED':
                    if not has_label:
                        continue
                    log.info('watching new secret %s/%s',
                             secret_ns, secret_name)
                    new_secret = WatchedSecret(secret_name, secret_ns)
                    self.watched_secrets[secret_name] = new_secret
                    self.add_secret_to_matching_namespaces(new_secret, v1)

                elif type == 'DELETED':
                    if not has_label:
                        continue
                    log.info('stop watching secret %s/%s',
                             secret_ns, secret_name)
                    del self.watched_secrets[secret_name]
                elif type == 'MODIFIED':
                    log.info('modified: %s/%s', secret_ns, secret_name)
                    if has_label:
                        self.add_secret_to_matching_namespaces(new_secret, v1)
                    elif secret_name in self.watched_secrets:
                        del self.watched_secrets[secret_name]
                else:
                    log.warn('Unknown modification type: %s', type)

    def start(self):
        self.ns_thread = threading.Thread(target=self.watch_for_new_namespaces)
        self.sec_thread = threading.Thread(target=self.watch_for_new_secrets)

        self.ns_thread.start()
        self.sec_thread.start()

        self.ns_thread.join()
        self.sec_thread.join()


if __name__ == '__main__':
    namespace_to_watch = os.getenv.get('SECRET_REPLICATOR_NAMESPACE_TO_WATCH',
                                       None)
    if namespace_to_watch is None:
        raise ValueError('SECRET_REPLICATOR_NAMESPACE_TO_WATCH must be set')

    replicator = Replicator(namespace=namespace_to_watch)
    replicator.start()
