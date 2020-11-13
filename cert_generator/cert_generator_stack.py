import os
from aws_cdk import (
    core,
    aws_lambda as _lambda,
    aws_s3 as s3,
    aws_s3_deployment as s3deploy
)
from aws_cdk.aws_lambda_event_sources import S3EventSource as s3Event
from aws_cdk.aws_lambda_python import PythonFunction

dirname = os.path.dirname(__file__)

class CertGeneratorStack(core.Stack):

    def __init__(self, scope: core.Construct, id: str, config: dict, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        # S3 Bucket for persistence
        bucket = s3.Bucket(
            self,
            "Bucket",
        )

        # Deploy Templates
        s3deploy.BucketDeployment(
            self,
            "BucketDeploymentTemplates",
            sources=[s3deploy.Source.asset(os.path.join(dirname, "templates"))],
            destination_bucket=bucket,
            destination_key_prefix="templates"
        )

        # Create prefix for inputs
        s3deploy.BucketDeployment(
            self,
            "BucketDeploymentInputs",
            sources=[s3deploy.Source.asset(os.path.join(dirname, "inputs"))],
            destination_bucket=bucket,
            destination_key_prefix="inputs"
        )

        # Create a prefix for outputs
        s3deploy.BucketDeployment(
            self,
            "BucketDeploymentOutputs",
            sources=[s3deploy.Source.asset(os.path.join(dirname, "outputs"))],
            destination_bucket=bucket,
            destination_key_prefix="outputs"
        )

        core.CfnOutput(self, "Templates", value=bucket.s3_url_for_object("templates"))
        core.CfnOutput(self, "Inputs", value=bucket.s3_url_for_object("inputs"))
        core.CfnOutput(self, "Outputs", value=bucket.s3_url_for_object("outputs"))

        # wkhtmltopdf layer
        wkhtmltopdflayer = _lambda.LayerVersion(
            self,
            'wkhtmltopdflayer',
            code=_lambda.AssetCode(
                os.path.join(dirname, "layers/wkhtmltox.zip")
            ),
            compatible_runtimes = [_lambda.Runtime.PYTHON_3_8]
        )

        # Cert Generator Lambda Function
        function = PythonFunction(
            self,
            "Function",
            runtime=_lambda.Runtime.PYTHON_3_8,
            entry=os.path.join(dirname, "lambda"),
            index="cert_generator.py",
            handler="lambda_handler",
            timeout=core.Duration.minutes(15),
            layers=[wkhtmltopdflayer]
        )
        function.add_environment("FONTCONFIG_PATH", "/opt/fonts")


        # Listen
        function.add_event_source(
            s3Event(
                bucket,
                events=[s3.EventType.OBJECT_CREATED],
                filters=[s3.NotificationKeyFilter(prefix="inputs/", suffix=".csv")]
            )
        )
        bucket.grant_read_write(function)


