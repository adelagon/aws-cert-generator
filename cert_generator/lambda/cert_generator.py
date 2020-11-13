import os
import sys
import csv
import boto3
import pdfkit

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
            
        
        # Generate Certificates

        ## wkhtmltopdf configurations
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
        with open(file_name) as csv_file:
            csv_reader = csv.DictReader(csv_file, delimiter=',')
            for row in csv_reader:
                msg = body.format(
                    fullname=row['Full Name'],
                    date=row['Date']
                )    
                certificate = open(os.path.join("templates", template, "certificate.html"), "w")
                certificate.write(msg)
                certificate.close()
                pdfkit.from_file(
                    (os.path.join("templates", template, "certificate.html")),
                    (os.path.join("templates", template, "certificate.pdf")),
                    configuration=config,
                    options=options
                )
                bucket.upload_file(
                    os.path.join("templates", template, "certificate.pdf"),
                    os.path.join("outputs/{}/certificate-{}.pdf".format(template, row['Full Name'])))
