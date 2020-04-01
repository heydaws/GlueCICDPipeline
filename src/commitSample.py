import boto3
import subprocess
import time
import urllib
import sys
import os

client = boto3.client('iam')
codecommit = boto3.client('codecommit')


user = sys.argv[1]
reponame = sys.argv[2]

path = os.getcwd() + '/' + reponame
print path

response = client.create_service_specific_credential( UserName=user, ServiceName='codecommit.amazonaws.com')
ccresponse = codecommit.get_repository(repositoryName=reponame)
credentialId = response["ServiceSpecificCredential"]["ServiceSpecificCredentialId"]
GitUsername = response["ServiceSpecificCredential"]["ServiceUserName"]
GitPassword = urllib.quote_plus(response["ServiceSpecificCredential"]["ServicePassword"])
url = ccresponse["repositoryMetadata"]["cloneUrlHttp"][8:]
url = "https://{0}:{1}@".format(GitUsername, GitPassword) + url
time.sleep(30)
subprocess.check_call(["git", "clone", url])
subprocess.check_call("cp -r *.yaml " +reponame, shell=True)
subprocess.check_call("cp -r *.py " +reponame, shell=True)
os.chdir( path )
subprocess.check_call("git add .", shell=True)
subprocess.check_call("git commit -m initialcommit", shell=True)
subprocess.check_call("git push", shell=True)
response = client.delete_service_specific_credential(UserName=user,ServiceSpecificCredentialId=credentialId)