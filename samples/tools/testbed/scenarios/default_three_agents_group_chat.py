from autogen import AssistantAgent, UserProxyAgent, GroupChat, GroupChatManager, config_list_from_json
import os
import json
import testbed_utils

testbed_utils.init()
##############################

# Construct a better AssistantAgent prompt for group chat
assistant_prompt = AssistantAgent.DEFAULT_SYSTEM_MESSAGE.strip().split("\n")
assistant_prompt[
    -1
] = "Reply with 'TERMINATE' if the task seems complete, everyone has had a chance to speak, and all parties seem satisfied."
assistant_prompt = "\n".join(assistant_prompt)

config_list = config_list_from_json(
    "OAI_CONFIG_LIST",
    filter_dict={"model": ["__MODEL__"]},
)

assistant = AssistantAgent(
    "coder",
    system_message=assistant_prompt,
    is_termination_msg=lambda x: x.get("content", "").rstrip().find("TERMINATE") >= 0,
    llm_config={
        "timeout": 180,  # Remove for autogen version >= 0.2, and OpenAI version >= 1.0
        "config_list": config_list,
    },
)
user_proxy = UserProxyAgent(
    "user_proxy",
    human_input_mode="NEVER",
    system_message="A human who can run code at a terminal and report back the results.",
    is_termination_msg=lambda x: x.get("content", "").rstrip().find("TERMINATE") >= 0,
    code_execution_config={
        "work_dir": "coding",
        "use_docker": False,
    },
    max_consecutive_auto_reply=10,
)
third_agent = AssistantAgent(
    "__THIRD_AGENT_NAME__",
    system_message="__THIRD_AGENT_PROMPT__",
    is_termination_msg=lambda x: x.get("content", "").rstrip().find("TERMINATE") >= 0,
    llm_config={
        "timeout": 180,  # Remove for autogen version >= 0.2, and OpenAI version >= 1.0
        "config_list": config_list,
    },
)

groupchat = GroupChat(agents=[user_proxy, assistant, third_agent], messages=[], max_round=12)

manager = GroupChatManager(
    groupchat=groupchat,
    is_termination_msg=lambda x: x.get("content", "").rstrip().find("TERMINATE") >= 0,
    llm_config={
        "timeout": 180,  # Remove for autogen version >= 0.2, and OpenAI version >= 1.0
        "config_list": config_list,
    },
)

user_proxy.initiate_chat(manager, message="__PROMPT__")


##############################
testbed_utils.finalize(agents=[assistant, user_proxy, third_agent, manager])
