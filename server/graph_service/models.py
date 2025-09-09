from typing import Optional
from pydantic import BaseModel, Field


# Custom entity types
class Team(BaseModel):
    """A team that contains one or more team members"""

    team_name: Optional[str] = Field(None, description='The name of the team'
)

class TeamMember(BaseModel):
    """A team member, which is a person who is a member of one or more teams"""

    team_member_name: Optional[str] = Field(None, description='The name of the team member')
    team_member_email: Optional[str] = Field(None, description='The email of the team member')
    team_member_login: Optional[str] = Field(None, description='The login/username of the team member')


class KubeResource(BaseModel):
    """A Kubernetes resource"""

    namespace: Optional[str] = Field('', description='The namespace of the resource')
    kind: Optional[str] = Field('', description='The kind of the resource')
    component: Optional[str] = Field('', description='The component of the resource')


class ContainerImage(BaseModel):
    """A container image"""

    image: Optional[str] = Field('', description='The name of the image')
    pipelineLink: Optional[str] = Field(
        default=None, description='The TeamCity link of the pipeline'
    )
    pipelineConfigId: Optional[str] = Field(
        default=None, description='The TeamCity build config id of the pipeline'
    )


class Cluster(BaseModel):
    """A Kubernetes cluster"""


class GitRepo(BaseModel):
    """A Git repository"""

    # org: Optional[str] = Field("", description="The organization of the repository")
    url: Optional[str] = Field('', description='The URL of the repository')


# class Project(BaseModel):
#     """A project"""

#     description: str | None = Field(default=None, description="General project info")


# Custom edge types
class IsMemberOf(BaseModel):
    """A relationship between a parent and a child"""


class IsGitOpsRepoFile(BaseModel):
    """A relationship between a parent and a child"""

    file_path: Optional[str] = Field('', description='The file path of the resource in the GitRepo')
    github_link: Optional[str] = Field('', description='The GitHub link of the resource')


class IsOwnedBy(BaseModel):
    """A resource is owned by a team"""


class IsCodeRepo(BaseModel):
    """A relationship between a parent and a child"""


class IsDeployedTo(BaseModel):
    """A relationship between a parent and a child"""


class IsInstanceOf(BaseModel):
    """A relationship between a parent and a child"""

    instance: Optional[str] = Field('', description='The name of the instance')
    component: Optional[str] = Field('', description='The component of the instance')
    portal_link: Optional[str] = Field('', description='The HTTP link of the portal page')


entity_types = {
    # "Project": Project,
    'Team': Team,
    'TeamMember': TeamMember,
    'KubeResource': KubeResource,
    'ContainerImage': ContainerImage,
    'Cluster': Cluster,
    'GitRepo': GitRepo,
}
edge_types = {
    'IsMemberOf': IsMemberOf,
    'IsOwnedBy': IsOwnedBy,
    'IsGitOpsRepoFile': IsGitOpsRepoFile,
    'IsCodeRepo': IsCodeRepo,
    'IsDeployedTo': IsDeployedTo,
    'IsInstanceOf': IsInstanceOf,
}
edge_type_map = {
    # ("Project", "Team"): ["IsOwnedBy"],
    ('Team', 'TeamMember'): ['IsMemberOf'],
    ('KubeResource', 'Project'): ['IsInstanceOf'],
    ('KubeResource', 'Cluster'): ['IsDeployedTo'],
    # ("Project", "GitRepo"): ["IsGitOpsRepoFile", "IsCodeRepo"],
    # ("Project", "Cluster"): ["IsDeployedTo"],
    ('ContainerImage', 'KubeResource'): ['IsDeployedTo'],
    ('Entity', 'Entity'): ['RELATES_TO'],
}
