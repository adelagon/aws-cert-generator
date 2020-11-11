#!/usr/bin/env python3
import yaml
from aws_cdk import core

from cert_generator.cert_generator_stack import CertGeneratorStack

config = yaml.load(open('./config.yaml'), Loader=yaml.FullLoader)

app = core.App()

env = core.Environment(region=config["region"])
stack_name = config["stack_name"] + "-" + config["environment"]
CertGeneratorStack(app, stack_name, config, env=env)

app.synth()
