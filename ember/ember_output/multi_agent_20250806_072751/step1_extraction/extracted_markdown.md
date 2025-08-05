# Generated from multi_agent.ipynb
## Markdown cells extracted in order


---
<!-- Cell 1 -->

# Multi-Agent Workflows + RAG - LangGraph

Today we'll be looking at an example of a Multi-Agent workflow that's powered by LangGraph, LCEL, and more!

We're going to be, more specifically, looking at a "heirarchical agent teams" from the [AutoGen: Enabling Next-Gen LLM
Applications via Multi-Agent Conversation](https://arxiv.org/pdf/2308.08155) paper.

This will be the final "graph" of our system:

![image](https://i.imgur.com/Xro0QiR.png)

It's important to keep in mind that the actual implementation will be constructed of 3 separate graphs, the final one having 2 graphs as nodes! LangGraph is a heckuva tool!

---
<!-- Cell 2 -->

# 🤝 BREAKOUT ROOM #1

---
<!-- Cell 3 -->

## Dependencies

---
<!-- Cell 4 -->

Since we'll be relying on OpenAI's suite of models to power our agents today, we'll want to provide our OpenAI API Key.

We're also going to be using the Tavily search tool - so we'll want to provide that API key as well!

Instruction for how to obtain the Tavily API key can be found:

1. [Tavily API Key](https://app.tavily.com/sign-in)

---
<!-- Cell 6 -->

## Task 1: Simple LangGraph RAG

Now that we have our dependencies set-up - let's create a simple RAG graph that works over our Loan PDFs from previous sessions.

> NOTE: While this particular example is very straight forward - you can "plug in" any complexity of chain you desire as a node in a LangGraph.

---
<!-- Cell 7 -->

## Retrieval

The 'R' in 'RAG' - this is, at this point, fairly straightforward!

---
<!-- Cell 8 -->

#### Data Collection and Processing

A classic first step, at this point, let's grab our desired document!

---
<!-- Cell 10 -->

Now we can chunk it down to size!

---
<!-- Cell 12 -->

Now we've successfully split our single PDF into...

---
<!-- Cell 14 -->

documents!

---
<!-- Cell 15 -->

#### Embedding Model and Vector Store

Now that we have our chunked document - lets create a vector store, which will first require us to create an embedding model to get the vector representations of our text!

We'll use OpenAI's [`text-embedding-3-small`](https://platform.openai.com/docs/guides/embeddings/embedding-models) model - as it's cheap, and performant.

---
<!-- Cell 17 -->

Now we can create our QDrant backed vector store!

---
<!-- Cell 19 -->

Let's make sure we can access it as a retriever.

---
<!-- Cell 21 -->

### Augmented

Now that we have our retrieval process set-up, we need to set up our "augmentation" process - AKA a prompt template.

---
<!-- Cell 23 -->

### Generation

Last, but certainly not least, let's put the 'G' in 'RAG' by adding our generator - in this case, we can rely on OpenAI's [`gpt-4o-mini`](https://platform.openai.com/docs/models/gpt-4o-mini) model!

---
<!-- Cell 25 -->

### RAG - Retrieval Augmented Generation

All that's left to do is combine our R, A, and G into a single graph - and we're off!

---
<!-- Cell 28 -->

Let's test this out and make sure it works.

---
<!-- Cell 30 -->

### RAG Limitation

Notice how we're hard-coding our data, while this is simply meant to be an illustrative example - you could easily extend this to work with any provied paper or document in order to have a more dynamic system.

For now, we'll stick with this single hard-coded example in order to keep complexity down in an already very long notebook!

---
<!-- Cell 31 -->

##### 🏗️ Activity #1 (Bonus Marks)

Allow the system to dynamically fetch Arxiv papers instead of hard coding them.

> HINT: Tuesday's assignment will be very useful here.

---
<!-- Cell 33 -->

## Task 2: Helper Functions for Agent Graphs

We'll be using a number of agents, nodes, and supervisors in the rest of the notebook - and so it will help to have a collection of useful helper functions that we can leverage to make our lives easier going forward.

Let's start with the most simple one!

---
<!-- Cell 34 -->

#### Import Wall

Here's a wall of imports we'll be needing going forward!

---
<!-- Cell 36 -->

### Agent Node Helper

Since we're going to be wrapping each of our agents into a node - it will help to have an easy way to create the node!

---
<!-- Cell 38 -->

### Agent Creation Helper Function

Since we know we'll need to create agents to populate our agent nodes, let's use a helper function for that as well!

Notice a few things:

1. We have a standard suffix to append to our system messages for each agent to handle the tool calling and boilerplate prompting.
2. Each agent has its our scratchpad.
3. We're relying on OpenAI's function-calling API for tool selection
4. Each agent is its own executor.

---
<!-- Cell 40 -->

### Supervisor Helper Function

Finally, we need a "supervisor" that decides and routes tasks to specific agents.

Since each "team" will have a collection of potential agents - this "supervisor" will act as an "intelligent" router to make sure that the right agent is selected for the right task.

Notice that, at the end of the day, this "supervisor" is simply directing who acts next - or if the state is considered "done".

---
<!-- Cell 42 -->

## Task 3: Research Team - A LangGraph for Researching Loan Policy

Now that we have our RAG chain set-up and some awesome helper functions, we want to create a LangGraph related to researching a specific topic, in this case: Loans!

We're going to start by equipping our Research Team with a few tools:

1. Tavily Search - aka "Google", for the most up to date information possible.
2. Our RAG chain - specific and high quality information about our topic.

Let's create those tools now!

---
<!-- Cell 43 -->

### Tool Creation

As you can see below, some tools already come pre-packaged ready to use!

---
<!-- Cell 45 -->

Creating a custom tool, however, is very straightforward.

> NOTE: You *must* include a docstring, as that is what the LLM will consider when deciding when to use this tool.

---
<!-- Cell 47 -->

> NOTE: We could just as easily use the LCEL chain directly, since nodes can be LCEL objects - but creating a tool helps explain the tool creation process at the same time.

---
<!-- Cell 48 -->

### Research Team State

Since we're using LangGraph - we're going to need state!

Let's look at how we've created our state below.

---
<!-- Cell 50 -->

Notice how we've used `messages`, `team_members`, and `next`.

These states will help us understand:

1. What we've done so far (`messages`)
2. Which team members we have access to (`team_members`)
3. Which team member is up next! (`next`)

---
<!-- Cell 51 -->

### Research Team LLM

We'll be using `gpt-4o-mini` today. This LLM is going to be doing a lot of reasoning - but we also want to keep our costs down, so we'll use a lightweight; but powerful, model!

---
<!-- Cell 53 -->

##### ❓ Question #1:

Why is a "powerful" LLM important for this use-case?

`Because we're using tools, and many tools can be selected based on context, an LLM with adequate reasoning capabilities is necessary in order to ensure reliable selection of the appropriate tool, especially as the tool list grows`

What tasks must our Agent perform that make it such that the LLM's reasoning capability is a potential limiter?

`In addition to tool selection described above, it would also need to understand the roles of other team members, passing the baton to them accordingly, as well as knowing when to end the chain.`

---
<!-- Cell 54 -->

### Research Team Agents & Nodes

Now we can use our helper functions to create our agent nodes, with their related tools.

Let's start with our search agent node.

---
<!-- Cell 55 -->

#### Research Team: Search Agent

We're going to give our agent access to the Tavily tool, power it with our GPT-4o Mini model, and then create its node - and name it `Search`.

---
<!-- Cell 57 -->

#### Research Team: RAG Agent Node

Now we can wrap our LCEL RAG pipeline in an agent node as well, using the LCEL RAG pipeline as the tool, as created above.

---
<!-- Cell 59 -->

### Research Team Supervisor Agent

Notice that we're not yet creating our supervisor *node*, simply the agent here.

Also notice how we need to provide a few extra pieces of information - including which tools we're using.

> NOTE: It's important to use the *exact* tool name, as that is how the LLM will reference the tool. Also, it's important that your tool name is all a single alphanumeric string!

---
<!-- Cell 61 -->

### Research Team Graph Creation

Now that we have our research team agent nodes created, and our supervisor agent - let's finally construct our graph!

We'll start by creating our base graph from our state, and then adding the nodes/agent we've created as nodes on our LangGraph.

---
<!-- Cell 63 -->

Now we can define our edges - include our conditional edge from our supervisor to our agent nodes.

Notice how we're always routing our agent nodes back to our supervisor!

---
<!-- Cell 65 -->

Now we can set our supervisor node as the entry point, and compile our graph!

---
<!-- Cell 67 -->

#### Display Graph

---
<!-- Cell 70 -->

The next part is key - since we need to "wrap" our LangGraph in order for it to be compatible in the following steps - let's create an LCEL chain out of it!

This allows us to "broadcast" messages down to our Research Team LangGraph!

---
<!-- Cell 72 -->

Now, finally, we can take it for a spin!

---
<!-- Cell 74 -->

##### 🏗️ Activity #2:

Using whatever drawing application you wish - please label the flow above on a diagram of your graph.

![Diagram](image.png)

---
<!-- Cell 75 -->

##### ❓ Question #2:

How could you make sure your Agent uses specific tools that you wish it to use? Are there any ways to concretely set a flow through tools?

`You could hardcode triggers/scenarios for tool calls if those conditions are met, and only if those conditions are met.`

---
<!-- Cell 76 -->

# 🤝 BREAKOUT ROOM #2

---
<!-- Cell 77 -->

## Task 4: Document Writing Team - A LangGraph for Planning, Writing, and Editing a Formal Complaint Response.

Let's run it all back, this time specifically creating tools, agent nodes, and a graph for Planning, Writing, and Editing a Formal Complaint Response!

---
<!-- Cell 78 -->

#### Previous Complaint Data

Let's add a retriever for [previous complaint data](./data/complaints.csv) here!

This will allow our response writing team reference previous responses!

---
<!-- Cell 82 -->

### Tool Creation

Let's create some tools that will help us understand, open, work with, and edit documents to our liking!

---
<!-- Cell 84 -->

##### 🏗️ Activity #3:

Describe, briefly, what each of these tools is doing in your own words.

1. `create_outline`: writes a list of main points into an outline file

2. `read_document`: can read all or a part of a given file

3. `write_document`: creates a new doc file with provided content

4. `reference_previous_responses`: searches complaint responses for similar cases

5. `edit_document`: modifies existing documents by inserting new text at specified lines

---
<!-- Cell 85 -->

### Document Writing State

Just like with our Research Team state - we want to keep track of a few things, however this time - we also want to keep track of which files we've created - so let's add that here!

---
<!-- Cell 87 -->

### Document Writing Prelude Function

Since we have a working directory - we want to be clear about what our current working directory looks like - this helper function will allow us to do that cleanly!

---
<!-- Cell 89 -->

### Document Writing Node Creation

---
<!-- Cell 91 -->

### Document Writing Team LangGraph Construction

This part is almost exactly the same (with a few extra nodes) as our Research Team LangGraph construction - so we'll leave it as one block!

---
<!-- Cell 93 -->

#### Display Graph

---
<!-- Cell 95 -->

Just as before - we'll need to create an "interface" between the level above, and our graph.

---
<!-- Cell 97 -->

Now we can test this out!

> NOTE: It is possible you may see an error here - rerun the cell to clear.

---
<!-- Cell 99 -->

## Task 5: Meta-Supervisor and Full Graph

Finally, now that we have our two LangGraph agents (some of which are already multi-agent), we can build a supervisor that sits above all of them!

The final process, surprisingly, is quite straight forward!

Let's jump in!

First off - we'll need to create our supervisor agent node.

---
<!-- Cell 101 -->

We'll also create our new state - as well as some methods to help us navigate the new state and the subgraphs.

> NOTE: We only pass the most recent message from the parent graph to the subgraph, and we only extract the most recent message from the subgraph to include in the state of the parent graph.

---
<!-- Cell 103 -->

Next, we'll create our base graph.

Notice how each node we're adding is *AN ENTIRE LANGGRAPH AGENT* (wrapped into an LCEL chain with our helper functions above).

---
<!-- Cell 105 -->

Next, we'll create our edges!

This process is completely idenctical to what we've seen before - just addressing the LangGraph subgraph nodes instead of individual nodes.

---
<!-- Cell 107 -->

That's it!

Now we can finally use our full agent!

---
<!-- Cell 109 -->

## SAMPLE POST!

---
<!-- Cell 110 -->

**Subject: Assistance Regarding Student Loans for Low-Income Students**

Dear [Customer's Name],

Thank you for reaching out regarding student loans and their implications for low-income students. We understand that navigating the financial aid landscape can be daunting, and we’re here to provide guidance and support.

Student loans are instrumental in granting low-income students access to higher education, especially when scholarships and grants may fall short of covering the full cost of attendance. The federal student loan program presents various options designed to make borrowing more manageable for those in need.

**1. Understanding Loan Types:**
   - **Subsidized Loans**: These loans are available to undergraduate students who demonstrate financial need. The government covers the interest while the borrower is enrolled at least half-time, which can significantly alleviate the overall debt burden upon graduation.
   - **Unsubsidized Loans**: Accessible to both undergraduate and graduate students, these loans do not require a demonstration of financial need. However, interest starts accruing from the moment the loan is disbursed.

**2. Income-Based Repayment Options:**
For low-income borrowers, Income-Based Repayment (IBR) plans can be especially advantageous. These plans ensure that monthly payments are based on income and family size, which helps keep payments manageable. Additionally, after 20-25 years of qualifying payments, any remaining loan balance may be eligible for forgiveness. 

**3. Key Benefits:**
   - **Lower Payments**: IBR plans decrease the monthly payment amount, making it easier for low-income students to manage their loans successfully.
   - **Forgiveness Opportunities**: Those who pursue careers in public service may qualify for further loan forgiveness options.

**4. The Importance of Financial Aid Awareness:**
It is vital for low-income students to be aware of their options concerning financial aid and student loans. We recommend that students and families familiarize themselves with the array of resources available, such as [Federal Student Aid](https://studentaid.gov), which provides comprehensive information on eligibility and application processes.

If you need further assistance or have specific questions, please don’t hesitate to reach out. Our goal is to ensure that every student can pursue their educational aspirations without the fear of overwhelming debt.

Best regards,

[Your Name]  
[Your Position]  
[Your Contact Information]  
[Your Organization]