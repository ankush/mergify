# -*- encoding: utf-8 -*-
#
# Copyright © 2021 Mergify SAS
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
import pytest

from mergify_engine import admin
from mergify_engine import config


@pytest.mark.recorder
async def test_suspended() -> None:
    await admin.suspended("PUT", config.TESTING_ORGANIZATION_NAME)
    await admin.suspended("DELETE", config.TESTING_ORGANIZATION_NAME)
