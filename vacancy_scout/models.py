from dataclasses import dataclass


@dataclass(frozen=True)
class Vacancy:
    title: str
    url: str
    company: str = ""
    location: str = ""
    posted: str = ""
