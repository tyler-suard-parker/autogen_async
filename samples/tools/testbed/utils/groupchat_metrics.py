import os
import errno
import shutil
import subprocess
import json
import sys
import time
import pathlib
import argparse
import re


def groupchat_metrics(results_dir):
    """
    Compute some standard metrics for GroupChat.

    Args:
        results_dir (path): The folder were results were be saved.
    """

    for test_id in os.listdir(results_dir):
        test_path = os.path.join(results_dir, test_id)

        # Metrics
        instance_metrics = dict()
        instance_metrics["n"] = 0
        instance_metrics["speaker_select_warnings"] = list()
        instance_metrics["speaker_counts"] = list()
        instance_metrics["consecutive_invocations"] = list()
        instance_metrics["empty_responses"] = list()
        instance_metrics["ended_with_terminate"] = list()
        instance_metrics["number_of_turns"] = list()

        instance = 0
        instance_dir = os.path.join(test_path, str(instance))
        while os.path.isdir(instance_dir):
            console_log_path = os.path.join(instance_dir, "console_log.txt")
            manager_messages_path = os.path.join(instance_dir, "chat_manager_messages.json")

            # load the data
            console_log = None
            with open(console_log_path, "rt") as fh:
                console_log = fh.read()

            manager_messages = None
            with open(manager_messages_path, "rt") as fh:
                manager_messages = json.loads(fh.read())

            # focus on the user_proxy messages, which should have a record of everything
            # TODO: Find a better global approach
            messages = manager_messages["user_proxy"]

            instance_metrics["n"] += 1
            instance_metrics["speaker_select_warnings"].append(console_log.count("GroupChat select_speaker failed"))

            speaker_counts = dict()
            consecutive_invocations = dict()
            empty_responses = dict()

            instance_metrics["speaker_counts"].append(speaker_counts)
            instance_metrics["consecutive_invocations"].append(consecutive_invocations)
            instance_metrics["empty_responses"].append(empty_responses)

            previous_name = None
            for m in messages:
                name = m["name"]
                if name not in speaker_counts:
                    speaker_counts[name] = 0
                if name not in consecutive_invocations:
                    consecutive_invocations[name] = 0
                if name not in empty_responses:
                    empty_responses[name] = 0

                speaker_counts[name] += 1
                if m["content"] is None or m["content"].strip() == "":
                    empty_responses[name] += 1

                if name == previous_name:
                    consecutive_invocations[name] += 1
                previous_name = name

            if len(messages) > 0 and "TERMINATE" in messages[-1]["content"]:
                instance_metrics["ended_with_terminate"].append(1)
            else:
                instance_metrics["ended_with_terminate"].append(0)

            instance_metrics["number_of_turns"].append(sum(speaker_counts.values()))

            instance += 1
            instance_dir = os.path.join(test_path, str(instance))

        def avg(lst):
            if len(lst) == 0:
                return 0
            else:
                return sum(lst) / float(len(lst))

        def speaker_distributions(instances):
            if len(instances) == 0:
                return dict()
            counts = dict()
            mins = dict()
            maxes = dict()

            # Get all the speakers we could possibly know about
            speakers = list()
            for instance in instances:
                for speaker in instance:
                    if speaker not in speakers:
                        speakers.append(speaker)

            for instance in instances:
                for speaker in speakers:
                    count = 0
                    if speaker in instance:
                        count = instance[speaker]

                    if speaker not in counts:
                        counts[speaker] = 0
                        mins[speaker] = count
                        maxes[speaker] = count

                    counts[speaker] += count
                    maxes[speaker] = max(maxes[speaker], count)
                    mins[speaker] = min(mins[speaker], count)

            result = ""
            for speaker in counts:
                label = speaker
                while len(label) < 24:
                    label = " " + label

                counts[speaker] = counts[speaker] / len(instances)
                result += f"    {label}: AVG {counts[speaker]} (MIN {mins[speaker]}, MAX {maxes[speaker]})\n"
            return result

        print("Test Id: " + test_id)
        print("Number of instances: " + str(instance_metrics["n"]))
        print(
            "Instances with select_speaker warnings: "
            + str(sum([min(1, w) for w in instance_metrics["speaker_select_warnings"]]))
        )
        print("Instances ending with TERMINATE: " + str(sum(instance_metrics["ended_with_terminate"])))
        print(
            "Number of turns: AVG "
            + str(avg(instance_metrics["number_of_turns"]))
            + " (MIN "
            + str(min(instance_metrics["number_of_turns"]))
            + ", MAX "
            + str(max(instance_metrics["number_of_turns"]))
            + ")"
        )
        print(
            "Average number of select_speaker warnings: AVG "
            + str(avg(instance_metrics["speaker_select_warnings"]))
            + " (MIN "
            + str(min(instance_metrics["speaker_select_warnings"]))
            + ", MAX "
            + str(max(instance_metrics["speaker_select_warnings"]))
            + ")"
        )
        print("\nSpeaking time (turns):\n")
        print(speaker_distributions(instance_metrics["speaker_counts"]))
        print("\nConsecutive invocations (usually indicative of orchestration failure):\n")
        print(speaker_distributions(instance_metrics["consecutive_invocations"]))
        print(
            "\nEmpty responses:\n(0 or 1 wasted GPT call for each user_proxy case, and 2 wasted GPT calls otherwise):\n"
        )
        print(speaker_distributions(instance_metrics["empty_responses"]))
        # print("Raw data: ")
        # print(json.dumps(instance_metrics, indent=4))


###############################################################################
if __name__ == "__main__":
    script_path = os.path.realpath(__file__)
    script_name = os.path.basename(script_path)
    script_dir = os.path.dirname(script_path)

    # Path to the default results directory
    # (relative to this script, up on directory, then into the results folder)
    default_results_dir = os.path.realpath(
        os.path.join(script_dir, os.path.pardir, "results", "default_three_agents_group_chat_gpt4")
    )

    parser = argparse.ArgumentParser(
        description=f"""
{script_name} compute some common metrics for GroupChat settings.
""".strip(),
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "scenario",
        nargs="?",
        help="Path to the scenario results. (default: " + default_results_dir + ")",
        default=default_results_dir,
    )
    args = parser.parse_args()
    groupchat_metrics(args.scenario)
