#!/usr/bin/env python3

from aws_cdk import core

from cert_generator.cert_generator_stack import CertGeneratorStack


app = core.App()
CertGeneratorStack(app, "cert-generator")

app.synth()
