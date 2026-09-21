# Copyright (C) 2026 Synopsys, Inc. and ANSYS, Inc. All rights reserved.
# SPDX-License-Identifier: MIT
#
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""Configuration for MCP tool test modules."""

import ansys.geometry.core as pyansys_geometry
import pytest


@pytest.fixture(scope="session")
def use_existing_service(request):
    value: str = request.config.getoption("--use-existing-service")
    return True if value.lower() == "yes" else False


@pytest.fixture(scope="session", autouse=True)
def use_tracker(request):
    """Fixture to enable or disable the tracker."""
    value: str = request.config.getoption("--use-tracker", default="no")  # Explicitly set default

    if value.lower() == "yes":
        pyansys_geometry.USE_TRACKER_TO_UPDATE_DESIGN = True
    else:
        pyansys_geometry.USE_TRACKER_TO_UPDATE_DESIGN = False

    yield  # This allows the test to run

    # Revert the state after the test session
    pyansys_geometry.USE_TRACKER_TO_UPDATE_DESIGN = False


@pytest.fixture(scope="session")
def transport_mode(request):
    """Fixture to determine transport mode to be used."""

    value: str = request.config.getoption("--transport-mode", default="insecure")

    return value.lower()


def pytest_addoption(parser):
    parser.addoption(
        "--use-existing-service",
        action="store",
        default="no",
        help=(
            "Use Modeler object to connect to an existing service. Options: 'yes' or 'no'."
            " By default, 'no'."
        ),
        choices=("yes", "no"),
    )
    parser.addoption(
        "--use-tracker",
        action="store",
        default="no",
        help=("Enable the tracker to update the design. Options: 'yes' or 'no'. By default, 'no'."),
        choices=("yes", "no"),
    )
    parser.addoption(
        "--transport-mode",
        action="store",
        default="insecure",
        help=("Specify the transport mode to use for the tests. By default, 'insecure'."),
        choices=("insecure", "uds", "wnua", "mtls"),
    )
    parser.addoption(
        "--run-llm-eval",
        action="store_true",
        default=False,
        help=(
            "Run the LLM tool-discoverability evaluation in tests/eval. Requires Azure OpenAI"
            " credentials in the environment. Skipped by default."
        ),
    )
    parser.addoption(
        "--llm-eval-repeats",
        action="store",
        type=int,
        default=5,
        help="Number of times each evaluation prompt is sent to the model. By default, 5.",
    )
    parser.addoption(
        "--llm-eval-threshold",
        action="store",
        type=float,
        default=0.8,
        help="Minimum fraction of repeats that must select the expected tool. By default, 0.8.",
    )
    parser.addoption(
        "--llm-eval-report",
        action="store",
        default="tests/logs/llm_eval_report.json",
        help="Path of the JSON report written by the evaluation suite.",
    )
