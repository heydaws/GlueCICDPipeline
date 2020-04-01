import unittest
import sys
import boto3
import filecmp
import time

glue = boto3.client('glue')
client = boto3.client('cloudformation')
athena = boto3.client('athena')
s3 = boto3.client('s3')

def getStackResources(stackname):
	response = client.describe_stack_resources(StackName=stackname)
	return response['StackResources'] 

def deleteDatabase(databasename):
	try:
		glue.delete_database(Name=databasename)	
	except :
		print("table "+ databasename + " did not exists")

def getcrawlerDatabase(crawlername):
	response = glue.get_crawler(Name=crawlername)
	return 	response['Crawler']['DatabaseName']

def runCrawler(crawlername):
	glue.start_crawler(Name=crawlername)
	response = glue.get_crawler(Name=crawlername)
	state = response['Crawler']['State']
	while state == 'RUNNING' or state == 'STOPPING':
		time.sleep(60)
		response = glue.get_crawler(Name=crawlername)
		state = response['Crawler']['State']
	print "final state " + state	
	print "last crawl " + response['Crawler']['LastCrawl']['Status']	
	return response['Crawler']['LastCrawl']['Status']

def runJob(jobname):
	response = glue.start_job_run(JobName=jobname)
	jobRunid = response['JobRunId']
	response = glue.get_job_run(JobName=jobname,RunId=jobRunid)
	state = response['JobRun']['JobRunState']
	print "state " + state
	while state == 'RUNNING':
		time.sleep(180)
		response = glue.get_job_run(JobName=jobname,RunId=jobRunid)
		state = response['JobRun']['JobRunState']
		print "state " + state
	print "final state " + state	
	return state


class MyTestCase(unittest.TestCase):
  def test_data_lake(self):
    resources_raw = getStackResources(self.STACKNAME)
    resourcesdict = {}
    for resource in resources_raw:
    	resourcesdict[resource['LogicalResourceId']] = resource['PhysicalResourceId']
    sourceDatabase = getcrawlerDatabase(resourcesdict['rawcrawler'])
    destinationDatabase = getcrawlerDatabase(resourcesdict['datalakecrawler'])
    
    #delete previous created databases
    deleteDatabase(sourceDatabase)
    deleteDatabase(destinationDatabase)

    #evaluate first crawlers
    self.assertEqual(runCrawler(resourcesdict['rawcrawler']), 'SUCCEEDED')
    
    #evaluate glue job
    self.assertEqual(runJob(resourcesdict['etljob']), 'SUCCEEDED')
    
    #evaluate result crawler
    self.assertEqual(runCrawler(resourcesdict['datalakecrawler']), 'SUCCEEDED')

    #evaluate athena query of results have expected value
    response = athena.start_query_execution(QueryString='select count(*) from '+destinationDatabase+'.datalake;', ResultConfiguration={'OutputLocation': 's3://'+resourcesdict['binariesBucket']+'/livetestquery1/'})
    key = 'livetestquery1/' + response['QueryExecutionId'] + '.csv'
    time.sleep(5)
    s3.download_file(resourcesdict['binariesBucket'], key , 'result.csv')
    result = open('result.csv', 'r').read() 
    self.assertEqual(result, '"_col0"\n"1070262"\n')    

if __name__ == '__main__':
  if len(sys.argv) > 1:
        MyTestCase.STACKNAME = sys.argv.pop()
  unittest.main()
