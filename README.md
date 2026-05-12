# Assistant Analytics - Analysis of AI Assistant Usages

Hello reader. This is all stuff related to **OpenFN**, a non-profit company that produces a software designed to help buisnesses create automated workflows for stuff like accounting, email management, all sorts of bureaucracy. One of the features of their software is an AI assistant that users can ask for help with building their workflow. I was given the data set of all the prompts and responses to this AI assistant and asked to explore how it is used. I did this by using Claude AI to *vibe code* a bunch of python programs that would analyse the data and create visualisations. The beauty of these being python programs, is that these guys can rerun these programs whenever they like, and get pretty graphs with updated results for their new data set, yippee!


#### omit-user-cleanup.py
This takes the core dataset *staff_messages_alltime_no-meta_no-code.csv* , and omits data associated with several users who are openfn staff that spend time debugging the assistant itself. If this wasn't omitted it would bias the data. It outputs *staff-chat-messages-filtered.csv* which is the input for most of the rest of these programs.

#### sys-vol-viz.py
This creates a visualisation that shows the monthly message volume, the core systems used and whether the user was using job_code or workflow_template. OpenFN has over 80 compatible systems so this is by no means exhaustive. Also note that after February 19th job_code and workflow_template have been integrated together so from then on everything just shows as workflow_template. The output is *monthly_volume_systems_used.png*

#### heuristic-response-time-v-lang-used.py
This one doesn't work that well because it's just heuristically using python to detect languages. To get it to run use:
`pip install langdetect langcodes`
then:
`pip install language_data`
The output is *heuristic_response_time_vs_language_used.png* 

#### broken-code-string-state.py
This looks for the string ")(state)" in the code column, which is indicative of a bug in the javascript code because openfn uses a weird type of javascript. The output is *broken_code_string_state.png*

#### gradient-response-time-viz.py
This creates *gradient_response_time.png*, a colour graded visualisation that shows how the response time of the assistant varies by month.

#### maximum-monthly-response-time-viz.py
Makes a graph of the top five prompts with the worst response time for each month. Output is *maximum_monthly_response_time.png*

#### monthly-response-time-viz.py
Makes a graph of the mean response time for all the prompts each month. Outputs *monthly_response_time.png*

#### median-monthly-response-time-viz.py
Makes a graph of the median response time for all the prompts each month. Outputs *median_monthly_response_time.png*

#### median-weekly-response-time-viz.py
Does the same as above but weekly. Outputs *median_weekly_response_time.png*

#### monthly-response-time-ses-typ-viz.py
This shows how the response type varies between job_code and workflow_template sessions, note that job_code and workflow_template merged on February 19th and are counted all as workflow_template from then on. Outputs *monthly_response_time_by_session_type.png*

#### percent-30s-quality-standard.py
This shows the percentage of prompts each month that had a response time over 30s, a big red flag for user experience. Outputs *percent_30s_quality_standard_viz.png*

#### response-time-viz.py
This creates a histogram to show the distribution of how the response time varies. Higher response time is bad so we want to shift this distribution towards the left! Outputs *response-time-histogram.png*

#### response-time-v-prompt-length.py
This explores whether the number of characters in the user's prompt caused an increase in response time (it doesn't seem to). Outputs *response_time_vs_prompt_character_length.png*


### Advanced Analysis via Anthropic API

To get deeper insight into the data set it was analysed using AI tools. Anthropic's API has a file size limit for how large a prompt can be, so in order to use it to analyse the data set it first had to be split up (parsed) into individual chat sessions.

#### sessio-parse.py
This parses staff-chat-messages-filtered.csv into thousands of individual files for each chat session that are stored in *C:\openfn\assistant-analytics\data\session_parsed*
These individually parsed sessions have a small enough file size that they can be sent directly to Claude's API for advanced analysis.

#### parsed-session-claude-analyser.py
This is the important one, it sends the parsed data in *C:\openfn\assistant-analytics\data\session_parsed* directly to the anthropic AI for advanced analysis using a prompt written in *C:\openfn\assistant-analytics\claude_prompt.txt* along with a list of OpenFN compatible adaptors stored in *C:\openfn\assistant-analytics\data\adaptors_list.txt* and a template for the output format *C:\openfn\assistant-analytics\data\claude_analysis_output_example_template.csv* . The data is output to *C:\openfn\assistant-analytics\data\session_parsed_analysis_data_output*
To run it you need an anthropic API key and to first run these commands
`pip install anthropic`
`set ANTHROPIC_API_KEY=sk-ant-api03-RT0Rlg7_...`  (put your own API key after the = sign)

#### session_parsed_analysis_unparser.py
This takes the anthropic API analysed data from *C:\openfn\assistant-analytics\data\session_parsed_analysis_data_output* and concatenates it back into a single file stored in *C:\openfn\assistant-analytics\data\anthropic_api_session_parsed_analysis.csv*

#### adaptors_network_graph_viz.py
This is a fun one, it produces a network graph of how frequently different adaptors are used in combination with each other. Have a look at these in the charts folder they are cool. It takes *C:\openfn\assistant-analytics\data\anthropic_api_session_parsed_analysis.csv* as the input and outputs to *C:\openfn\assistant-analytics\charts\adaptors_used_network_graph_viz.png*
To run it:
`pip install networkx`
`python C:\openfn\assistant-analytics\adaptors_network_graph_viz.py`
If you write a specific adaptor name after the program name when you run it, then it will produce a network graph that only shows nodes and edges connected to that specific adaptor, e.g.
`python C:\openfn\assistant-analytics\adaptors_network_graph_viz.py http` will produce a chart called *adaptors_used_network_graph_viz_http.png* that shows only how the http adaptor is used in combination with other adaptors.

#### comprehensive_tone_analysis_viz.py
This makes a bunch of percentage bar graps that display answers to a bunch of different questions about the actual content of the prompts like their tone, writing style, if claude thought that the problem was actually resolved, if the user sounded frustrated, if the session sounded like it was intended for building or debugging etc. These are all subjective questions but it's nice to have some sort of automated insight into them. Take the results for language? with a pinch of salt, it's not easy to confidently identify a language based on short prompts, and there is no dedicated list of supported languages for OpenFN's assistant. Takes *C:\openfn\assistant-analytics\data\anthropic_api_session_parsed_analysis.csv* as the input and outputs to *C:\openfn\assistant-analytics\charts\comprehensive_tone_analysis_viz.py*

#### response-time-v-adaptor-viz.py
Potentially a quite interesting one that shows how the average response time varies by adaptor used. Response time is calculated by averaging the difference between input_at and processing_completed_at for all the prompts in a session (ignoring any that are missing one or both of those values, which is a lot), and then averaging that to give the mean response time for each session. Then this script looks at *anthropic_api_session_parsed_analysis.csv* to see which sessions contain both data in the mean_response_time and adaptors_mentioned_in_user_prompt_specifically columns, and produces a bar graph that shows the mean average mean_response_time for each adaptor with interquartile range error bars. I.e it first takes the mean response time within a session, and then takes a mean again between sessions. Outputs *response_time_v_adaptor_viz.png* 

#### session-length-v-adaptor-viz.py
This is probably less useful, it shows how the length of a chat session varies by the adaptor used. The length of a session is calculated as the difference between the earliest input_at and the latest processing_completed_at time data within each session. Input is *anthropic_api_session_parsed_analysis.csv* and output is *session-length-v-adaptor-viz.png*





















