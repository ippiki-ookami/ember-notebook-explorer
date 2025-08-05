
Loom Link: [Cursor - ember2_working.ipynb - ember_extension [WSL: Ubuntu] - Cursor - 6 August 2025](https://www.loom.com/share/a0f5c4db210147c89f52ca7544d8b3b9)


**Notes:**
- I apologize, I was running different trials, changes, and what not as I was trying to decide what to do/how to work with, so the only applicable document for the non-UI portion right now is */ember-notebook-explorer/ember/ember2_working.ipynb*. Currently, the UI is still having issues so not everything is hooked up properly.
- I've also included an Obsidian Canvas file for the workflow for the LLM app in */ember-notebook-explorer/deliverables/workflow_planning.canvas
- This is not an excuse, I'll still gracefully accept a fail if appropriate, but just so it's not taken as laziness or lack of ambition, I'd just like to explain. I know I didn't complete everything - I jumped around a lot with how I wanted to do things, decided on something with complicated UI integration, focused too much on getting UI to work first instead of focusing on the LLM aspect, and then lost 2 days I was expecting to work on it because I had a depressive episode. So while I have most of the foundation up and running, I wasn't able to complete the evaluations and a functioning UI.



# 1: The Problem

When seeing code for the first time, especially for those less familiar, it can be overwhelming to understand it, especially when so often the code is presented in a linear fashion but the workflow itself is non-linear.

### Expanded Problem

What I noticed in class was often, myself and classmates would be confused by a piece of code, or need further explanation, or guidance as to where it fit into the overall notebook. I thought it would be useful to have an application that could be used as a study assistant and standalone explainer for code that other students and I could possibly use when trying to understand something during individual study. 

ChatGPT can answer questions, yes, but it needs to generally take into context everything again. Additionally, it can be very exhaustive scrolling back to previous questions that have been answered, since questions are answered in a sequential, single row fashion. Also, code is usually explained in relation to other code elsewhere in the codebase, and while ChatGPT can give you snippets of the code related, unless you already know how it functions, not knowing where that code fits in the overall context of adjacent code can affect understanding.


# 2: The Solution

My solution is a visual code walkthrough assistant. I initially spent time trying to implement it via a web app using React, but then came to realize that VS Code already has lots of built-in functionality that would be better suited for what I had in mind. The UI is planned to be a combination of tree view, graph view, code view, walkthrough, and LLM-assisted chat. 

The code would first be separated into Python and Markdown, so any previous explanation doesn't muddy analysis. Then the code would be analyzed, creating a codebase overview summary, distinguishing different "blocks" for the walkthrough, attributing code to each of those blocks, and basic explanation of the function of each of those blocks. 

From there, components would be extracted for each block (i.e. classes, functions, imports, etc.), as well as their edges to other components, and their function explained. At this point, block objects are converted into their relevant BlockStates, since there's a dependency resolution loop that makes sure that any component dependent on another component waits for that component to have its description generated before generating its own, so it has full context of its function.

Afterwards, a "deep description" is made for each block, taking into account the overview of the codebase, initial description of the block, the explanation of its components, and any relationships/edges to other blocks and components. It goes through iterative improvement after all blocks have generated their in-depth explanation and the codebase overview is also updated, checking to see if there's been any improvement.

All four would have mirrored function in regards to quoted or mentioned code components. Let's say you click on a component in the graph view - it would then highlight that component in the tree view and bring you to and highlight that component in the notebook view and the walkthrough. The walkthrough itself would also have linked mentions of components in its explanations so you can visualize where it fits in the workflow and see it in the context of the code. Asking the LLM assistant would also generate answers with clickable components, and the answer itself would be stored in the corresponding component, so that the component/snippet questioned about would now have a marker on all corresponding views where you could hover or click on something that would then show previous question/answer for it, making it easy to review it in case you forget its function, without scrolling endlessly in the LLM chat for it.

### Tools

a) **LLM:** combination of 4.1-nano and o4-mini-high (for initial code explanation)
b) **Embedding Model:** 
c) **Orchestration:**
d) **Vector Database:** Qdrant
e) **Monitoring:** LangSmith Tracing
f) **Evaluation:** ChatGPT and LangSmith
g) **User Interface:** VS Code



# 3: Data

1) Data sources would include both AIE session notebooks as well as ChatGPT generated notebooks. The session notebooks are applicable as they were the inspiration for the application in the first place, and so being able to have the application work for them is critical. ChatGPT-generated notebooks would be for additional generalization. Additionally, ChatGPT notebooks (in different levels of complexity) I find more reliable than just finding notebooks online, since ChatGPT would already have pre-planned the notebook it generated, and thus its "ground truth" is more reliable since it wrote the notebook, than having it analyze a notebook for accuracy.
2) Chunking per phase, and per component (with phases as parent documents). This allows easy navigation of both finding fine-grained or more general descriptive information, but allows for easy navigation for related components and edges to then follow in order to add context for appropriate response. Code itself will also be embedded and BM25 used with a hybrid retrieval according to descriptive and code specific relevance. 



# 4: Prototype


# 5: Golden Dataset

As mentioned, the datasets will be a mixture of AIE notebooks and ChatGPT-generated ones for some evaluations. This will be used to assess the following:
- component extraction (ChatGPT-generated will be best for testing this)
- cohesiveness of block separation and walkthrough flow
- accuracy of code understanding/explanation/coverage

For query evaluation, RAGAS will be performed using SDG from LangChain. I'm not sure how it would work since it's unconventional, at least to what we were exposed to in class, but I would have RAGAS generate questions, pass those questions to the ChatGPT instance that generated the synthetic notebook, and use those answers as ground truth since it has the context of the notebook generation. It should still be applicable because in theory, the query LLM never actually sees the "full code context" the same way that ChatGPT does.

# 6: Advanced Retrieval

As previously mentioned in the chunking section, I'll be making use of parent-document retrieval as well as hybrid retrieval with BM25. This way we can cover a combination of code string-literals and descriptive context. Additionally, multi query retrieval will likely be included, since there are several areas a code might be called for context, and being able to include all of them via different queries, and then reranking with Cohere, would provide the best of all worlds.

# 7: Performance Assessment
