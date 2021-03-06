{{/* vim: set filetype=mustache: */}}
{{/*
Expand the name of the chart.
*/}}
{{- define "secret-replicator.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{/*
Create a default fully qualified app name.
We truncate at 63 chars because some Kubernetes name fields are limited to this (by the DNS naming spec).
If release name contains chart name it will be used as a full name.
*/}}
{{- define "secret-replicator.fullname" -}}
{{- if .Values.fullnameOverride -}}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- $name := default .Chart.Name .Values.nameOverride -}}
{{- if contains $name .Release.Name -}}
{{- .Release.Name | trunc 63 | trimSuffix "-" -}}
{{- else -}}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}
{{- end -}}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "secret-replicator.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "secret-replicator.serviceAccountName" -}}
{{- if .Values.serviceAccount.name -}}
{{- .Values.serviceAccount.name -}}
{{- else -}}
{{- $fullName := include "secret-replicator.fullname" . -}}
{{- printf "%s-service-account" $fullName | trunc 63 | trimSuffix "-" -}}
{{- end -}}
{{- end -}}

{{- define "secret-replicator.rbacRoleName" -}}
{{- $fullName := include "secret-replicator.fullname" . -}}
{{- printf "%s-role" $fullName | trunc 63 | trimSuffix "-" -}}
{{- end -}}

{{- define "secret-replicator.rbacRoleBindingName" -}}
{{- $fullName := include "secret-replicator.fullname" . -}}
{{- printf "%s-role-binding" $fullName | trunc 63 | trimSuffix "-" -}}
{{- end -}}
