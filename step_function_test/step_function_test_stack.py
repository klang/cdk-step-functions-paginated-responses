from aws_cdk import (
    # Duration,
    Stack,
    aws_stepfunctions as sfn,
    aws_stepfunctions_tasks as sfn_tasks,
    # aws_sqs as sqs,
)
from constructs import Construct

class StepFunctionTestStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)


        describe_workspaces = sfn_tasks.CallAwsService(
            self,
            id="DescribeWorkspaces",
            comment="Get workspaces",
            service="workspaces",
            action="describeWorkspaces",
            result_path="$.DescribeWorkspacesResult",
            iam_resources=["*"],
        )
        
        describe_more_workspaces = sfn_tasks.CallAwsService(
            self,
            id="DescribeMoreWorkspaces",
            comment="Get workspaces with NextToken",
            service="workspaces",
            action="describeWorkspaces",
            parameters={
                "NextToken": sfn.JsonPath.string_at(
                    "$.DescribeWorkspacesResult.NextToken"
                )
            },
            result_path="$.DescribeWorkspacesResult",
            iam_resources=["*"],
        )
        
        rebuild_workspaces = sfn_tasks.CallAwsService(
            self,
            id="RebuildWorkspaces",
            comment="Rebuild workspaces",
            service="workspaces",
            action="rebuildWorkspaces",
            parameters={
                "RebuildWorkspaceRequests": [
                    {"WorkspaceId": sfn.JsonPath.string_at("$.WorkspaceId")}
                ]
            },
            result_path="$.RebuildWorkspacesResult",
            iam_resources=["*"],
        )
        rebuild_each_workspace = sfn.Map(
            self,
            id="RebuildEachWorkspace",
            comment="Rebuild each workspace",
            items_path="$.DescribeWorkspacesResult.Workspaces",
            output_path=sfn.JsonPath.DISCARD,
        )
        #https://github.com/aws/aws-cdk/issues/4417
        rebuild_each_workspace.iterator(sfn.Pass(self, "Map State"))
        
        definition = describe_workspaces.next(rebuild_each_workspace).next(
            sfn.Choice(self, "ChoiceMoreWorkspaces")
            .when(
                sfn.Condition.is_present("$.DescribeWorkspacesResult.NextToken"),
                describe_more_workspaces.next(rebuild_each_workspace),
            )
            .otherwise(sfn.Succeed(self, "Done"))
        )

        state_machine = sfn.StateMachine(
            self,
            id="WorkSpacesRebuilderStateMachine",
            state_machine_type=sfn.StateMachineType.STANDARD,
            definition=definition,
        )