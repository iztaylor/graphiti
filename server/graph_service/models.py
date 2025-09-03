from typing import Optional
from pydantic import BaseModel, Field


class Team(BaseModel):
    team: Optional[str] = Field("", description="The name of the team")


# class Project(BaseModel):
#     """A project"""

#     description: str | None = Field(default=None, description="General project info")


class KubeResource(BaseModel):
    """A Kubernetes resource"""

    namespace: Optional[str] = Field("", description="The namespace of the resource")
    kind: Optional[str] = Field("", description="The kind of the resource")
    component: Optional[str] = Field("", description="The component of the resource")


class ContainerImage(BaseModel):
    """A container image"""

    image: Optional[str] = Field("", description="The name of the image")
    pipelineLink: Optional[str] = Field(
        default=None, description="The TeamCity link of the pipeline"
    )
    pipelineConfigId: Optional[str] = Field(
        default=None, description="The TeamCity build config id of the pipeline"
    )


class Cluster(BaseModel):
    """A Kubernetes cluster"""


class GitRepo(BaseModel):
    """A Git repository"""

    #org: Optional[str] = Field("", description="The organization of the repository")
    url: Optional[str] = Field("", description="The URL of the repository")


class IsMemberOf(BaseModel):
    """A relationship between a parent and a child"""


class IsGitOpsRepoFile(BaseModel):
    """A relationship between a parent and a child  """

    file_path: Optional[str] = Field("", description="The file path of the resource in the GitRepo")
    github_link: Optional[str] = Field("", description="The GitHub link of the resource")


class IsOwnedBy(BaseModel):
    """A resource is owned by a team"""


class IsCodeRepo(BaseModel):
    """A relationship between a parent and a child"""


class IsDeployedTo(BaseModel):
    """A relationship between a parent and a child"""


class IsInstanceOf(BaseModel):
    """A relationship between a parent and a child"""

    instance: Optional[str] = Field("", description="The name of the instance")
    component: Optional[str] = Field("", description="The component of the instance")
    portal_link: Optional[str] = Field("", description="The HTTP link of the portal page")


entity_types = {
    # "Project": Project,
    "Team": Team,
    "KubeResource": KubeResource,
    "ContainerImage": ContainerImage,
    "Cluster": Cluster,
    "GitRepo": GitRepo,
}
edge_types = {
    "IsMemberOf": IsMemberOf,
    "IsOwnedBy": IsOwnedBy,
    "IsGitOpsRepoFile": IsGitOpsRepoFile,
    "IsCodeRepo": IsCodeRepo,
    "IsDeployedTo": IsDeployedTo,
    "IsInstanceOf": IsInstanceOf,
}
edge_type_map = {
    # ("Project", "Team"): ["IsOwnedBy"],
    ("KubeResource", "Project"): ["IsInstanceOf"],
    ("KubeResource", "Cluster"): ["IsDeployedTo"],
    # ("Project", "GitRepo"): ["IsGitOpsRepoFile", "IsCodeRepo"],
    # ("Project", "Cluster"): ["IsDeployedTo"],
    ("ContainerImage", "KubeResource"): ["IsDeployedTo"],
    ("Entity", "Entity"): ["RELATES_TO"],
}
