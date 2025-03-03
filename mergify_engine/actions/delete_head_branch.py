# -*- encoding: utf-8 -*-
#
#  Copyright © 2018 Mehdi Abaakouk <sileht@sileht.net>
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

import typing
from urllib import parse

import voluptuous

from mergify_engine import actions
from mergify_engine import check_api
from mergify_engine import context
from mergify_engine import rules
from mergify_engine import signals
from mergify_engine.clients import http
from mergify_engine.rules import conditions


class DeleteHeadBranchAction(actions.Action):
    flags = (
        actions.ActionFlag.ALLOW_AS_ACTION
        | actions.ActionFlag.DISALLOW_RERUN_ON_OTHER_RULES
        | actions.ActionFlag.ALLOW_ON_CONFIGURATION_CHANGED
        | actions.ActionFlag.ALWAYS_SEND_REPORT
    )
    validator = {voluptuous.Required("force", default=False): bool}

    async def run(
        self, ctxt: context.Context, rule: rules.EvaluatedRule
    ) -> check_api.Result:
        if ctxt.pull_from_fork:
            return check_api.Result(
                check_api.Conclusion.SUCCESS, "Pull request come from fork", ""
            )

        if not self.config["force"]:
            pulls_using_this_branch = [
                pull
                async for pull in ctxt.client.items(
                    f"{ctxt.base_url}/pulls",
                    resource_name="pulls",
                    page_limit=20,
                    params={"base": ctxt.pull["head"]["ref"]},
                )
            ] + [
                pull
                async for pull in ctxt.client.items(
                    f"{ctxt.base_url}/pulls",
                    resource_name="pulls",
                    page_limit=5,
                    params={"head": ctxt.pull["head"]["label"]},
                )
                if pull["number"] is not ctxt.pull["number"]
            ]
            if pulls_using_this_branch:
                pulls_using_this_branch_formatted = "\n".join(
                    f"* Pull request #{p['number']}" for p in pulls_using_this_branch
                )
                return check_api.Result(
                    check_api.Conclusion.NEUTRAL,
                    "Not deleting the head branch",
                    f"Branch `{ctxt.pull['head']['ref']}` was not deleted "
                    f"because it is used by:\n{pulls_using_this_branch_formatted}",
                )

        ref_to_delete = parse.quote(ctxt.pull["head"]["ref"], safe="")
        try:
            await ctxt.client.delete(f"{ctxt.base_url}/git/refs/heads/{ref_to_delete}")
        except http.HTTPClientSideError as e:
            if e.status_code == 404 or (
                e.status_code == 422 and "Reference does not exist" in e.message
            ):
                return check_api.Result(
                    check_api.Conclusion.SUCCESS,
                    f"Branch `{ctxt.pull['head']['ref']}` does not exist",
                    "",
                )
            else:
                return check_api.Result(
                    check_api.Conclusion.FAILURE,
                    "Unable to delete the head branch",
                    f"GitHub error: [{e.status_code}] `{e.message}`",
                )
        await signals.send(
            ctxt.repository,
            ctxt.pull["number"],
            "action.delete_head_branch",
            signals.EventNoMetadata(),
            rule.get_signal_trigger(),
        )
        return check_api.Result(
            check_api.Conclusion.SUCCESS,
            f"Branch `{ctxt.pull['head']['ref']}` has been deleted",
            "",
        )

    async def cancel(
        self, ctxt: context.Context, rule: "rules.EvaluatedRule"
    ) -> check_api.Result:  # pragma: no cover
        return actions.CANCELLED_CHECK_REPORT

    async def get_conditions_requirements(
        self,
        ctxt: context.Context,
    ) -> typing.List[
        typing.Union[conditions.RuleConditionGroup, conditions.RuleCondition]
    ]:
        return [
            conditions.RuleCondition(
                "closed", description=":pushpin: delete_head_branch requirement"
            )
        ]
