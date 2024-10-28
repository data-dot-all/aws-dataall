# **Worksheets**

data.all offers a rich editor to write SQL queries and explore data. It is Athena on the backend that runs our queries
on environments where our teams have been onboarded.


## :material-new-box: **Create a Worksheet**
On the left pane under **Play** click on **Worksheets** to go to the Worksheet menu. Here you will find all
Worksheets owned by your teams.

!!! success "Shared queries = Seamless Collaboration"
    Check, learn from and collaborate with other members of your team to improve your analyses and get insights from
    your data, directly from data.all worksheets. No need to send queries by email, no need to create views :)


To create a new worksheet click on the **Create** button in the top right corner and fill the Worksheet form:

![worksheets](pictures/worksheets/ws_form.png#zoom#shadow)

| Field             | Description                                | Required | Editable |Example
|-------------------|--------------------------------------------|----------|----------|-------------
| Worksheet name    | Name of the worksheet                      | Yes      | Yes      |PalmDor
| Short description | Short description about the worksheet      | No       | Yes      |Query used to retrieve Palm D'or winners
| Team              | Team that owns the worksheet               | Yes      | No       |DataScienceTeam
| Tags              | Tags  | No       | Yes      |adhoc

!!! note "No AWS resources"
    When we are creating a worksheet we are NOT deploying AWS resources. We don't provision clusters, we are not creating
    tables or views. We simply store the query in data.all database and we run it serverlessly on AWS Athena.


## :material-pencil-outline: **Edit worksheet metadata**
Select a worksheet and click on the pencil icon to edit the metadata of the worksheet. This includes worksheet name,
description and tags. The ownership of the worksheet, its team, is not editable.

## :material-trash-can-outline: **Delete a worksheet**
Next to the edit button, there are 2 other buttons. To delete a worksheet click on the trash icon one. Worksheets
are not AWS resources, they are a data.all construct whose information is stored in the data.all database. Thus,
when we delete a worksheet we are not deleting AWS resources or CloudFormation stacks.

## :material-database-search: **Write and save your queries**
Select your worksheet and choose any of the environments, datasets and tables of your team to list column information.
In the query editor write your SQL statements and click on **Run Query** to get your query results. Error messages
coming from Athena will pop-up automatically.

![worksheets](pictures/worksheets/ws_joins.png#zoom#shadow)

If you want to save the current query for later or for other users, click on the **save** icon (next to the edit and the
delete buttons).

!!! success "More than just SELECT"
    Worksheets can be used for data exploration, for quick ad-hoc queries and for more complicated queries that require
    joins. As far as you have access to the joined datasets you can combine information from multiple tables or datasets.
    Check the <a href="https://docs.aws.amazon.com/athena/latest/ug/select.html" target="_blank">docs</a>
    for more information on AWS Athena SQL syntax.


## :material-new-box: **Experimental Features: GenAI Powered Worksheets**

As part of data.all >= v2.7 we introduced support for generative AI powered worksheet features. These features include both:

1. Natural Language Querying (NLQ) of Structured Data
2. Text Document Analysis of Unstructured Data

These features are optionally enabled/disabled via feature flags specified in data.all's configuration.

More details on how to use each of these features are below.

### Natural Language Querying (NLQ) of Structured Data

data.all offers a NLQ feature to significantly reduce the barrier to entry for non-technical business users who need to quickly and easily query data to make informed decisions.

Given a prompt and a selection of tables, data.all NLQ feature will generate the corresponding SQL statement that data.all users can execute against the data they have access to in data.all's Worksheets module.

To start generating SQL, data.all users can select the TextToSQL Tab in the Worksheets View:

![worksheets_nlq](pictures/worksheets/ws_text_to_sql.png#zoom#shadow)

Users select the Worksheet environment, database and one or more tables where the data of interest is stored. Then they introduce a prompt describing the operation they want to perform. For example, they could type something like "Give me the top 3 clients in the last 10 months". Once they send the request to generate the query, data.all will invoke Claude 3.5 Sonnet model using Amazon Bedrock to generate a response.

To enrich the context of the genAI request, data.all fetches the Glue metadata of the tables and database and passes it to the LLM. Access to Glue is limited to the tables the user has access to, in other words, we control that only accessible glue tables are fetched.

In addition, there are built in guardrails to avoid mutating SQL statements (i.e. WRITE, UPSERT, DELETE, etc.).

data.all Admins can additionally limit the number of invocations run against these LLMs by specifying a `max_count_per_day` feature flag in data.all's configuration (please reference data.all's [Deployment Guide](https://data-dot-all.github.io/dataall/deploy-aws/#configjson) for more information).


### Text Document Analysis of Unstructured Data

For unstructured text documents, data.all offers a feature to start analyzing your data using natural language.

Given a prompt and a selected text docuemnt in a S3 Dataset, data.all's Document Analyzer feature will generate a response displayed in the data.all Worksheet Editor. 

!!! warning "Limitations of Document Analysis"
    Currently data.all's Worksheet Document Analyzer is limited only to `.txt` and `.pdf` file extensions. Additionally, the feature is limited only to 
    text documents which are explicitly owned by one of the user's teams (documents that are given access via data.all shares are not yet supported).


To start analyzing your text documents, data.all users can select the Document Analyzer Tab in the Worksheets View:

![worksheets_unstructured](pictures/worksheets/ws_analyze_txt_doc.png#zoom#shadow)

Users select the Worksheet environment, S3 dataset bucket and S3 object key (.txt or .pdf file) where the data of interest is stored. Then they introduce a prompt describing the information they want from the text document. For example, they could type something like "Give me the most prevalent 3 themes across this document". Once they send the request, data.all will invoke Claude 3.5 Sonnet model using Amazon Bedrock to generate a response.

data.all fetches the content of the S3 Object and passes it to the LLM along with the user prompt. Access to S3 is limited to the buckets the user owns.

There are built in guardrails to reduce hallucinations by ensuring the selected S3 Object contains information pertaining to the user's prompt.

data.all Admins can additionally limit the number of invocations run against these LLMs by specifying a `max_count_per_day` feature flag in data.all's configuration (please reference data.all's [Deployment Guide](https://data-dot-all.github.io/dataall/deploy-aws/#configjson) for more information).

