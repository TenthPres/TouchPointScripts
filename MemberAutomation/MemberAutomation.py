# this is an IronPython script for MembershipAutomation in BVCMS
# the variable p has been passed in and is the person that we are saving Member Profile information for

#import useful constants (defined in constants.py)
from constants import *

# cleanup for deceased and for dropped memberships
def DropMembership(p, Db):
    if p.MemberStatusId == MemberStatusCode.Member:
        p.DropDate = p.Now().Date
        if p.Deceased:
            p.DropCodeId = DropTypeCode.Deceased
            p.DropDate = p.Deceased  # TODO check that this is date
        p.MemberStatusId = MemberStatusCode.Previous

    if p.Deceased:
        p.EmailAddress = None
        p.EmailAddress2 = None
        p.DoNotCallFlag = True
        p.DoNotVisitFlag = True

        if p.SpouseId is not None:
            spouse = Db.LoadPersonById(p.SpouseId)

            if p.Deceased:
                spouse.MaritalStatusId = MaritalStatusCode.Widowed
                if spouse.EnvelopeOptionsId is not None: # not null
                    if spouse.EnvelopeOptionsId != EnvelopeOptionCode.NoEnvelope:
                        spouse.EnvelopeOptionsId = EnvelopeOptionCode.Individual
                spouse.ContributionOptionsId = EnvelopeOptionCode.Individual

            if spouse.MemberStatusId == MemberStatusCode.Member:
                if spouse.EnvelopeOptionsId == EnvelopeOptionCode.Joint:
                    spouse.EnvelopeOptionsId = EnvelopeOptionCode.Individual

        p.EnvelopeOptionsId = EnvelopeOptionCode.NoEnvelope
        p.DropAllMemberships(Db)


# -------------------------------------
# Main Function
class MembershipAutomation(object):
    def __init__(self):
        pass

    def Run(self, Db, p):
        p.errorReturn = "ok"

        if p.DeceasedDateChanged:
            if p.DeceasedDate is not None:
                DropMembership(p, Db)
