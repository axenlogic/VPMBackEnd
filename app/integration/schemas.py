from pydantic import BaseModel, Field
from typing import Optional


class IntegrationTokenRequest(BaseModel):
    client_id: str
    client_secret: str


class IntegrationTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class StudentInfo(BaseModel):
    first_name: str = Field(..., alias="firstName")
    last_name: str = Field(..., alias="lastName")
    grade: Optional[str] = None
    school: Optional[str] = None
    date_of_birth: str = Field(..., alias="dateOfBirth")
    student_id: str = Field(..., alias="studentId")


class ParentInfo(BaseModel):
    father_name: Optional[str] = Field(None, alias="fatherName")
    email_address: str = Field(..., alias="emailAddress")
    phone: str


class SchoolInfo(BaseModel):
    school_name: Optional[str] = Field(None, alias="schoolName")
    district_name: Optional[str] = Field(None, alias="districtName")
    school_id: Optional[str] = Field(None, alias="schoolId")
    district_id: Optional[str] = Field(None, alias="districtId")


class VerifyStudentRequest(BaseModel):
    student: StudentInfo
    parent: ParentInfo
    school: SchoolInfo


class VerifyStudentResponse(BaseModel):
    verified: bool
    match_level: str = Field(..., alias="matchLevel")
    reason: Optional[str] = None
    student: Optional[StudentInfo] = None
    parent: Optional[ParentInfo] = None
    school: Optional[SchoolInfo] = None

    class Config:
        populate_by_name = True

