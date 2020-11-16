import os
import sys
import csv
import uuid
import boto3
import pdfkit

class SafeDict(dict):
    def __missing__(self, key):
        return '{' + key + '}'

def lambda_handler(context, event):
    s3 = boto3.resource('s3')
    os.chdir('/tmp')

    for record in context["Records"]:
        # Context Details
        object_key = record["s3"]["object"]["key"]
        bucket_name = record["s3"]["bucket"]["name"]
        file_name = object_key.split('/')[-1]
        bucket = s3.Bucket(bucket_name)

        # Download the csv file
        print("Downloading csv file: {}".format(file_name))
        bucket.download_file(
            object_key,
            file_name
        )

        # Download templates
        template = file_name.split('.')[0]
        if os.path.exists(os.path.join("templates", template)):
            print("Template already downloaded, skipping.")
        else:
            print("Downloading '{}' template...".format(template))
            for obj in bucket.objects.filter(Prefix="templates/{}/".format(template)):
                if not os.path.exists(os.path.dirname(obj.key)):
                    os.makedirs(os.path.dirname(obj.key))
                if obj.key[-1] == '/':
                    continue
                bucket.download_file(obj.key, obj.key)

        # wkhtmltopdf configurations
        config = pdfkit.configuration(wkhtmltopdf="/opt/bin/wkhtmltopdf")
        options = {
            'enable-local-file-access': None,
            'page-size': 'A4',
            'orientation': 'Landscape',
            'margin-top': '0.5in',
            'margin-right': '0.5in',
            'margin-bottom': '0.5in',
            'margin-left': '0.5in',
            'encoding': "UTF-8",
            'custom-header' : [
                ('Accept-Encoding', 'gzip')
            ],
            'no-outline': None
        }
        
        body = open(os.path.join("templates", template, "index.html")).read()
        with open(file_name, encoding="utf-8") as csv_file:
            csv_reader = csv.DictReader(csv_file, delimiter=",")
            fields = csv_reader.fieldnames
            
            # Prepare output.csv
            output_csv = open(os.path.join("templates", template, "output.csv"), "w")
            fields.append("Certificate URL")
            csv_writer = csv.DictWriter(output_csv, fieldnames=fields)
            csv_writer.writeheader()

            for row in csv_reader:
                # Inject values into templates
                msg = body.format_map(SafeDict(row))
                certificate = open(os.path.join("templates", template, "certificate.html"), "w")
                certificate.write(msg)
                certificate.close()

                # Generate to PDF
                pdfkit.from_file(
                    (os.path.join("templates", template, "certificate.html")),
                    (os.path.join("templates", template, "certificate.pdf")),
                    configuration=config,
                    options=options
                )

                # Upload to S3
                s3_object_name = os.path.join("outputs/{}/certificate-{}.pdf".format(
                        template,
                        uuid.uuid4().hex
                        )
                )

                bucket.upload_file(
                    os.path.join("templates", template, "certificate.pdf"),
                    s3_object_name    
                )

                # Generate Pre-signed URL (1-week)
                s3_client = boto3.client("s3")
                presigned_url = s3_client.generate_presigned_url('get_object',
                                                    Params={'Bucket': bucket_name,
                                                            'Key': s3_object_name},
                                                    ExpiresIn=os.environ['PRESIGNED_URL_EXPIRES'])
                
                # Update output.csv
                row["Certificate URL"] = presigned_url
                csv_writer.writerow(row)
            
            # Upload output.csv
            output_csv.close()
            bucket.upload_file(
                os.path.join("templates", template, "output.csv"),
                os.path.join("outputs/{}/output.csv".format(template))
            )