#Role=Admin
# RegistrationMigration.py
#
# Sample script: converts an Involvement from "Join Involvement" registration to "Registration
# Form", carrying over its settings, questions, historical registrants, answers, and payments.
#
# IMPORTANT LIMITATION, please read before using this on real data:
# The old system stores a registrant's submitted answers as a single XML blob on their roster row
# (OrganizationMembers.OnlineRegData) -- there is exactly one such blob per involvement/person pairing,
# so each new submission overwrites the previous one. Therefore, the database only ever reflects the
# MOST RECENT submission. The new Registration Forms overcome this limitation, but cannot magically
# recreate the historical registration information that has been overwritten.
#
# Earlier submissions aren't necessarily gone, though. Since mid-2022 every enrollment also appends its
# answers to dbo.OnlineOPRRegQA (with the enrollment's date and transaction id), which is never
# overwritten -- this script uses that first, so each past enrollment becomes its own dated Registration
# with its own payment. For enrollments before that table existed: while a registration is being filled out (and
# briefly afterward), TouchPoint also saves it as its own row in dbo.RegistrationData -- one row per
# separate registration SESSION, not per person, and never overwritten or automatically deleted. This
# script mines that table for other completed sessions that included this person besides the one
# their roster row currently points to, and uses those to recover the answers (and, via
# Transaction.DatumId, the payment) for each earlier submission. This is a best-effort recovery, not
# a guarantee -- if an earlier RegistrationData row was manually deleted (there's an admin action for
# that), or predates this mechanism, its answers really are gone, and this script falls back to a
# "payment-only" Registration (the payment preserved and linked, but no recovered answers).
#
# QUESTIONS: In addition to migrating past registration data, this script attempts to migrate the questions themselves
# from the old registration system to the new.  There isn't entirely a direct relationship between the old and the new,
# so always check to see if results are what you expect.
#
# Usage (paste into TouchPoint's admin "Special Content / PyScript" area and run as a report):
#   ?orgid=1234            preview everything this would do; changes nothing
#   ?orgid=1234&apply=1    do it: settings, questions, registrations, answers, payment links
#
# This does NOT flip the Involvement to Registration Form type -- do that separately with
# model.SetOrgRegistrationType once you've reviewed the result (see ValidateRegistrationMigration.sql).

from System.Xml.Linq import XElement

REGISTRATION_FORM_TYPE = 26

# --- Settings translation (Organizations.RegSettingXml -> Organizations.Reg* columns) -------------

SETTINGS_FIELD_MAP = {
    "Deposit": ("RegDepositAmount", float),
    "IncludeOtherFeesWithDeposit": ("RegDepositIncludesOtherFees", lambda v: v.lower() == "true"),
    "ApplyMaxToOtherFees": ("RegMaxFeeAppliesToOtherFees", lambda v: v.lower() == "true"),
    "HoursBeforeTicketSalesEnd": ("RegHoursBeforeTicketSalesEnd", int),
    "Subject": ("RegMessageConfirmationEmailSubject", str),
    "InstructionSorry": ("RegMessageClosed", str),
    "ThankYouMessage": ("RegMessageConfirmationPage", str),
    "OnEnrollScript": ("OnEnrollScript", str),
}


def xml_text(root, name):
    el = root.Element(name)
    if el is None or not el.Value:
        return None
    return el.Value


def find_account_code_id(code):
    if not code:
        return None
    row = q.QuerySqlTop1("select Id from AccountCodes where Code = '%s'" % code.replace("'", "''"))
    return row.Id if row else None


def parse_org_id(value):
    # GroupToJoin in the legacy Settings is a stringified OrganizationId (see
    # AddOrganizationController.Submit's oldsettings.GroupToJoin.ToInt2() usage); guard against it
    # being blank or otherwise not a plain integer.
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def get_legacy_settings_xml(org_id):
    row = q.QuerySqlTop1("select RegSettingXml from Organizations where OrganizationId = %d" % org_id)
    if row is None:
        raise Exception("no organization %d" % org_id)
    return row.RegSettingXml


def translate_settings(org_id, settings_xml):
    """Return the {ColumnName: value} dict for the Registration Form schema, translated from the
    legacy RegSettingXml plus the legacy Limit column. Returns {} if there's nothing to translate.
    NOTE: RegFeeType/RegFundId/RegMerchantId are Finance-role-gated by model.UpdateOrganization --
    this script never touches those (the old Settings.AccountingCode maps to RegAccountCodeId
    instead, which isn't restricted), so no special handling is needed here."""
    row = q.QuerySqlTop1("select [Limit] as LegacyLimit from Organizations where OrganizationId = %d" % org_id)
    settings = {}

    if row and row.LegacyLimit:
        settings["RegLimit"] = row.LegacyLimit

    if settings_xml:
        root = XElement.Parse(settings_xml)

        for xml_field, (column, convert) in SETTINGS_FIELD_MAP.items():
            value = xml_text(root, xml_field)
            if value is not None:
                settings[column] = convert(value)

        account_code_id = find_account_code_id(xml_text(root, "AccountingCode"))
        if account_code_id is not None:
            settings["RegAccountCodeId"] = account_code_id

        other_org_id = parse_org_id(xml_text(root, "GroupToJoin"))
        if other_org_id is not None:
            settings["RegJoinOtherOrgId"] = other_org_id

    return settings


# --- Question translation (RegSettingXml AskItems -> RegQuestion rows) -----------------------------

# Not a real per-person question -- an org-level "answers not required" marker. Never appears in
# OnlineRegPersonModel.Enroll.cs's SaveAnswers switch, so it has no answer to recover either.
EXCLUDED_ASK_TYPES = ("AnswersNotRequired",)

# A Label plus a list of Description/SmallGroup/Fee items. The "WithCondition"/"WithRedirect"
# variants add branching, which RegQuestionOption.SkipToId exists for in the new schema, but this
# script doesn't attempt to reconstruct that branching automatically -- their choices still convert,
# just as a flat (non-branching) list.
MULTI_CHOICE_ASK_TYPES = {
    "AskCheckboxes": {"item_element": "CheckboxItem", "question_type": 3, "question_subtype": 0},  # MultipleChoice
    "AskDropdown": {"item_element": "DropdownItem", "question_type": 6, "question_subtype": 0},  # DropDown
    "AskMenu": {"item_element": "MenuItem", "question_type": 6, "question_subtype": 1},  # DropDown / Menu (counts per item)
    "AskRadioButton": {"item_element": "RadioButtonItem", "question_type": 2, "question_subtype": 0},  # SingleChoice
    "AskDropdownWithCondition": {"item_element": "DropdownWithConditionItem", "question_type": 6, "question_subtype": 0},
    "AskRadioCondition": {"item_element": "RadioConditionItem", "question_type": 2, "question_subtype": 0},
    # These two item element names follow the same {Type}Item naming convention as the others but
    # weren't directly confirmed against source -- if a question of this type comes through with
    # zero options, check CmsData/RegistrationModels/AskDropdownWithRedirect.cs / AskRadioRedirect.cs.
    "AskDropdownWithRedirect": {"item_element": "DropdownWithRedirectItem", "question_type": 6, "question_subtype": 0},
    "AskRadioRedirect": {"item_element": "RadioRedirectItem", "question_type": 2, "question_subtype": 0},
}

TEXT_LIST_ASK_TYPES = ("AskText", "AskExtraQuestions")  # both wrap a list of plain {Question} prompts

# RegAnswerSaveAsEnum (Tps.Core.Entities.Registrations.Dto.RegSettingsEnum.cs): what the new form does
# with a person's answer beyond recording it.
SAVE_AS_ANSWER = 0
SAVE_AS_SUBGROUP = 1
SAVE_AS_EXTRA_VALUE = 2

# SmallGroup values the old forms reserved for rows that aren't real choices (a bolded heading with
# no checkbox, and a plain comment line) -- see AskCheckboxes.SmallGroups().
NON_CHOICE_SMALL_GROUPS = ("nocheckbox", "comment")

# Old choice-type questions put the person in a sub-group named for the choice, unless the question
# (its TargetExtraValue attribute) or the whole registration (Settings.TargetExtraValues) was set to
# write person extra values instead -- see OnlineRegPersonModel.Enroll.cs SaveCheckboxChoices et al.
# AskMenu has no extra-value branch in the old code: it always used sub-groups.
SUBGROUP_CHOICE_ASK_TYPES = ("AskCheckboxes", "AskDropdown", "AskRadioButton", "AskDropdownWithCondition",
                             "AskRadioCondition", "AskDropdownWithRedirect", "AskRadioRedirect", "AskMenu")
EXTRA_VALUE_CAPABLE_ASK_TYPES = ("AskText", "AskExtraQuestions", "AskYesNoQuestions") + tuple(
    t for t in SUBGROUP_CHOICE_ASK_TYPES if t != "AskMenu")


def save_value_as_for(ele, ask_type, org_target_extra_values):
    """Map the old per-question 'where does this answer go' behavior to a RegAnswerSaveAsEnum value."""
    target_attr = ele.Attribute("TargetExtraValue")
    target_extra = org_target_extra_values or (target_attr is not None and target_attr.Value.lower() == "true")
    if ask_type in EXTRA_VALUE_CAPABLE_ASK_TYPES and target_extra:
        return SAVE_AS_EXTRA_VALUE
    if ask_type in SUBGROUP_CHOICE_ASK_TYPES or ask_type == "AskYesNoQuestions":
        return SAVE_AS_SUBGROUP
    return SAVE_AS_ANSWER

# AskDocuments' answers ARE covered by the @question-attributed DocumentUpload node (already in
# PRIOR_SUBMISSION_ANSWER_NODES / the OnlineRegQA view), so it's handled like a normal question here
# and needs no special-casing beyond its QuestionType.
SINGLE_ANSWER_ASK_TYPES = {
    "AskDocuments": {"question_type": 7, "question_subtype": 0},  # FileUpload
    "AskSuggestedFee": {"question_type": 11, "question_subtype": 10},  # Money / SuggestedFee -- no
    # historical answer to recover; the old system never recorded one for this type.
}

# Structural/instructional -- no per-person answer at all.
STRUCTURAL_ASK_TYPES = ("AskHeader", "AskInstruction", "AskInstructionPlain", "AskInstruction2", "AskDivider")

# A single answer, or a handful of related fields joined into one readable string, read as plain
# XML element(s) (WriteXml's default reflection-based case) directly on the person's
# OnlineRegData/RegistrationData block -- not the @question-attributed pattern the other buckets use.
# Matched by ask type, not by question label.
# AskPassport's QUESTION is migrated but never its answers: its field list is empty on purpose, so no passport
# detail is ever read from the registration XML (and OnlineOPRRegQA's encrypted rows are skipped too).
# ask_type -> (question_type, question_subtype, [(xml_property, display_label_or_None), ...])
# These values are recorded as registration answers only. They are never copied onto the person's own
# record (cell phone, SMS opt-in, grade level, etc.): that would overwrite present state with whatever
# the person said at registration time, and this migration preserves history without changing the present.
SIMPLE_ELEMENT_ASK_TYPES = {
    "AskRequest": (1, 0, [("request", None)]),  # Text
    "AskTickets": (1, 0, [("ntickets", None)]),  # Text
    "AskPledge": (11, 8, [("Pledge", None)]),  # Money / Pledge
    "AskAllergies": (1, 3, [("medical", None)]),  # Text / Allergies
    "AskTylenolEtc": (3, 4, [("tylenol", "Tylenol"), ("advil", "Advil"),
                             ("robitussin", "Robitussin"), ("maalox", "Maalox")]),  # MultipleChoice / Medication
    "AskEmContact": (8, 0, [("emcontact", "Contact"), ("emphone", "Phone")]),  # EmergencyContact
    "AskInsurance": (13, 0, [("insurance", "Carrier"), ("policy", "Policy")]),  # Insurance
    "AskDoctor": (14, 0, [("doctor", "Doctor"), ("docphone", "Phone")]),  # Doctor
    "AskParents": (12, 0, [("mname", "Mother"), ("fname", "Father")]),  # Parents
    "AskPassport": (9, 0, []),  # Passport -- question only, no answers
    "AskCoaching": (2, 0, [("coaching", None)]),  # SingleChoice (Yes/No)
    "AskChurch": (3, 0, [("memberus", "Member here"), ("nochurch", "Not a member anywhere"),
                         ("otherchurch", "Attends another church")]),  # MultipleChoice
    "AskCellPhone": (1, 0, [("cellPhone", None)]),  # Text
    "AskSMS": (2, 0, [("sms", None)]),  # SingleChoice (Yes/No)
    "AskGradeOptions": (6, 11, [("gradeoption", None)]),  # DropDown / Grade
    "AskSize": (6, 2, [("shirtsize", None)]),  # DropDown / ShirtSize
}


def parse_multi_choice(ele, shape):
    label = xml_text(ele, "Label")
    options = []
    for item in ele.Elements(shape["item_element"]):
        description = xml_text(item, "Description")
        if not description:
            continue
        # The old reader defaults a missing SmallGroup to the description (see CheckboxItem.ReadXml).
        small_group = (xml_text(item, "SmallGroup") or description).strip()
        if small_group in NON_CHOICE_SMALL_GROUPS:
            continue  # display-only heading / comment row in the old form, not something a person picks
        fee_attr = item.Attribute("Fee")
        limit_attr = item.Attribute("Limit")  # only the checkbox/dropdown/radio/menu items have one
        option = {
            "Name": small_group,
            "Text": description,
            # The new system's SubGroup mode tags a person with the option's Value (falling back to
            # Text), so carrying the old SmallGroup in Value reproduces the same sub-group names. It
            # is also what the old form recorded as the answer, so recovered answers still match.
            "Value": small_group,
            "Fee": float(fee_attr.Value) if fee_attr is not None else None,
        }
        # The old form counted how many people already chose this item (via its sub-group) and
        # refused more once the limit was reached; the new form does the same with option.Limit,
        # counting sub-group members when the question saves to a sub-group.
        if limit_attr is not None and limit_attr.Value.isdigit() and int(limit_attr.Value) > 0:
            option["Limit"] = int(limit_attr.Value)
        options.append(option)
    if not label or not options:
        return []
    return [{
        "label": label,
        "question_type": shape["question_type"],
        "question_subtype": shape["question_subtype"],
        "options": options,
    }]


def parse_text_list(ele):
    # Each <Question> prompt becomes its own separate RegQuestion -- the old system bundled several
    # free-text prompts into one Ask node, the new one is one question per RegQuestion.
    questions = []
    for question_el in ele.Elements("Question"):
        label = question_el.Value
        if label:
            questions.append({"label": label, "question_type": 1, "question_subtype": 0, "options": []})  # Text
    return questions


def parse_yes_no(ele, save_as):
    questions = []
    for item in ele.Elements("YesNoQuestion"):
        label = xml_text(item, "Question")
        if not label:
            continue
        small_group = (xml_text(item, "SmallGroup") or label).strip()
        if save_as == SAVE_AS_SUBGROUP:
            # The old form tagged people "Yes:<SmallGroup>" / "No:<SmallGroup>" (SaveYesNoChoices).
            yes_value, no_value = "Yes:" + small_group, "No:" + small_group
        else:
            # Extra-value mode: the old form stored the extra value named for the question, set to
            # Yes or No. The new ExtraVal save uses Name as the value name and Value as its value.
            yes_value, no_value = "Yes", "No"
        questions.append({
            "label": label,
            "question_type": 2,  # SingleChoice
            "question_subtype": 0,
            "options": [
                {"Name": small_group, "Text": "Yes", "Value": yes_value},
                {"Name": small_group, "Text": "No", "Value": no_value},
            ],
        })
    return questions


def is_required(ele, ask_type):
    """Whether the legacy Ask element enforced an answer. Ask.WriteStartAttributes only emits
    Required="true" when set, and Ask.ReadAskAttributes treats a missing attribute as false (its
    constructor default of true is always overwritten on read), so absent means not required.
    AskAllergies is always read as not required regardless of the attribute. An AskDocuments element
    is also required if any of its individual OrganizationDocument entries is."""
    if ask_type == "AskAllergies":
        return False
    attr = ele.Attribute("Required")
    if attr is not None and attr.Value.lower() == "true":
        return True
    if ask_type == "AskDocuments":
        for document in ele.Elements("OrganizationDocument"):
            if (xml_text(document, "Required") or "").lower() == "true":
                return True
    return False


def parse_ask_items(settings_xml):
    """Parse RegSettingXml's <AskItems> into:
      - questions: list of {label, question_type, question_subtype, options, required, save_as, old_type, ask_type} dicts ready
        for AddRegQuestion (label is used as the answer-matching key for most types; SIMPLE_ELEMENT
        types are additionally keyed by ask_type -- see migrate_questions).
      - unhandled: raw element names this script doesn't recognize at all.
    """
    if not settings_xml:
        return [], []

    root = XElement.Parse(settings_xml)
    ask_items_el = root.Element("AskItems")
    if ask_items_el is None:
        return [], []

    org_target_extra_values = (xml_text(root, "TargetExtraValues") or "").lower() == "true"
    questions = []
    unhandled = []
    order = 0
    for ele in ask_items_el.Elements():
        ask_type = ele.Name.LocalName
        if ele.Attribute("Disabled") is not None and ele.Attribute("Disabled").Value.lower() == "true":
            continue  # disabled questions in the old system aren't shown; don't carry them forward

        if ask_type in EXCLUDED_ASK_TYPES:
            continue

        save_as = save_value_as_for(ele, ask_type, org_target_extra_values)

        if ask_type in MULTI_CHOICE_ASK_TYPES:
            parsed = parse_multi_choice(ele, MULTI_CHOICE_ASK_TYPES[ask_type])
        elif ask_type in TEXT_LIST_ASK_TYPES:
            parsed = parse_text_list(ele)
        elif ask_type == "AskYesNoQuestions":
            parsed = parse_yes_no(ele, save_as)
        elif ask_type in SIMPLE_ELEMENT_ASK_TYPES:
            q_type, q_subtype, _fields = SIMPLE_ELEMENT_ASK_TYPES[ask_type]
            label = xml_text(ele, "Label") or ask_type
            parsed = [{"label": label, "question_type": q_type, "question_subtype": q_subtype,
                       "options": [], "ask_type": ask_type}]
        elif ask_type in SINGLE_ANSWER_ASK_TYPES:
            shape = SINGLE_ANSWER_ASK_TYPES[ask_type]
            label = xml_text(ele, "Label") or ask_type
            parsed = [{"label": label, "question_type": shape["question_type"],
                       "question_subtype": shape["question_subtype"], "options": []}]
        elif ask_type in STRUCTURAL_ASK_TYPES:
            label = xml_text(ele, "Label") or ask_type
            parsed = [{"label": label, "question_type": 4, "question_subtype": 0, "options": []}]  # Instructions
        else:
            unhandled.append(ask_type)
            continue

        required = is_required(ele, ask_type)
        for question in parsed:
            question["required"] = required and ask_type not in STRUCTURAL_ASK_TYPES
            question["save_as"] = save_as
            question["old_type"] = ask_type
            if ask_type == "AskMenu":
                question["answer_kind"] = ("menu", [option["Name"] for option in question["options"]])
            elif ask_type == "AskYesNoQuestions":
                question["answer_kind"] = ("yesno",)
            question["order"] = order
            order += 1
            questions.append(question)

    return questions, unhandled


def migrate_questions(org_id, questions, apply_changes):
    """Create a RegQuestion for each parsed legacy question. Returns (question_map, type_map,
    answer_kinds): question_map is {label: RegQuestionId} for ordinary label-matched answers;
    type_map is {ask_type: RegQuestionId} for the SIMPLE_ELEMENT_ASK_TYPES questions, which are
    matched by ask type rather than by label; answer_kinds is {RegQuestionId: ("menu", [item names])
    or ("yesno",)} for the questions whose old answer text needs converting first (see
    prepare_answer). In preview mode (apply_changes=False), no questions are actually created, so the
    maps use the label/ask_type itself as a placeholder id, purely so migrate_member's
    answer-matching preview is accurate."""
    question_map = {}
    type_map = {}
    answer_kinds = {}
    for question in questions:
        print "  question: %r (type=%d/%d, %d option(s)%s%s)" % (
            question["label"], question["question_type"], question["question_subtype"], len(question["options"]),
            ", required" if question["required"] else "",
            {SAVE_AS_SUBGROUP: ", saves to sub-group", SAVE_AS_EXTRA_VALUE: ", saves to extra value"}.get(
                question["save_as"], ""))
        if apply_changes:
            reg_question_id = model.AddRegQuestion(
                org_id,
                question["order"],
                question["question_type"],
                question["label"],
                question["required"],
                question["options"],
                question["question_subtype"],
                question["save_as"],
            )
        else:
            reg_question_id = question["label"]
        question_map[question["label"]] = reg_question_id
        if "ask_type" in question:
            type_map[question["ask_type"]] = reg_question_id
        if "answer_kind" in question:
            answer_kinds[reg_question_id] = question["answer_kind"]
    return question_map, type_map, answer_kinds


def yes_no_text(value):
    """The old forms recorded a yes/no choice as a boolean's text ('True'/'False')."""
    return "Yes" if value.strip().lower() in ("true", "yes", "1") else "No"


# Simple-element types holding a single yes/no value (see SIMPLE_ELEMENT_ASK_TYPES).
YES_NO_SIMPLE_ASK_TYPES = ("AskCoaching", "AskSMS")


def prepare_answer(value, answer_kind=None, ask_type=None):
    """Turn a recovered old answer into what model.AddRegAnswer should be given. AddRegAnswer takes
    plain text (or a list) and does the JSON encoding itself -- including splitting a ', '-joined
    checkbox answer into its choices -- so most answers pass straight through. Only a few need
    translating first:
      - yes/no questions: 'True'/'False' -> 'Yes'/'No' (the new question's two options)
      - menu questions: the old 'item=count, item=count' text -> a list of counts in option order
    """
    if ask_type in YES_NO_SIMPLE_ASK_TYPES or (answer_kind and answer_kind[0] == "yesno"):
        return yes_no_text(value)
    if answer_kind and answer_kind[0] == "menu":
        counts = {}
        for pair in value.split(", "):
            if "=" in pair:
                name, count = pair.rsplit("=", 1)
                counts[name.strip()] = count.strip()
        return [counts.get(name, "") for name in answer_kind[1]]
    return value


# --- Registration / RegPeople / RegAnswer translation ----------------------------------------------

# CmsData.Codes.MemberTypeCode.Drop = -1, InActive = 230; RegPersonStatusCode: Completed = 2, Dropped = 3
def status_for_member(member):
    if member.MemberTypeId in (-1, 230) or member.InactiveDate is not None:
        return 3  # Dropped
    if member.Pending:
        return 1  # Pending
    return 2  # Completed


def get_roster(org_id):
    return q.QuerySql("""
        select om.PeopleId, om.MemberTypeId, om.Pending, om.EnrollmentDate, om.InactiveDate,
               om.Amount, om.AmountPaid, om.TranId, om.OnlineRegData, om.RegisterEmail,
               om.RegistrationDataId,
               p.FirstName, p.LastName, p.EmailAddress
        from OrganizationMembers om
        join People p on p.PeopleId = om.PeopleId
        where om.OrganizationId = %d
    """ % org_id)


def get_current_answers(org_id, people_id):
    """The (Question, Answer) pairs from this person's CURRENT OnlineRegData -- i.e. their most
    recent submission. Rows sharing the same Question via a repeating group ([set] > 0, e.g. "add
    another child") collapse to the first one seen; the rest are reported, not silently dropped."""
    rows = list(q.QuerySql("""
        select Question, Answer, [set]
        from OnlineRegQA
        where OrganizationId = %d and PeopleId = %d
        order by [set]
    """ % (org_id, people_id)))
    seen = {}
    skipped = []
    for row in rows:
        if row.Question in seen:
            skipped.append(row.Question)
            continue
        seen[row.Question] = row.Answer
    return seen, skipped


# Per-node answer extraction rule, matching exactly what the OnlineRegQA view does per node type
# (see CmsData/Migrations/20230208_..._OnlineRegQA_view.sql): most answer nodes hold their answer as
# their own inner text, but the four "WithCondition"/"WithRedirect" variants hold it in a nested
# <Value> child element instead.
PRIOR_SUBMISSION_ANSWER_NODES = {
    "ExtraQuestion": "text", "Text": "text", "YesNoQuestion": "text", "YesNo": "text",
    "DocumentUpload": "text", "RadioChoice": "text", "SelectOption": "text",
    "MultipleChoice": "text", "MenuChoice": "text",
    "SelectOptionWithCondition": "value_child", "RadioChoiceWithCondition": "value_child",
    "SelectOptionWithRedirect": "value_child", "RadioChoiceWithRedirect": "value_child",
}


def answers_from_person_element(person_el):
    """The (Question, Answer) pairs for one <OnlineRegPersonModel> block within a RegistrationData
    row's <List>. Mirrors get_current_answers' repeating-group handling: the first answer seen per
    Question wins, the rest are reported rather than silently dropped."""
    answers = {}
    skipped = []
    for node_name, answer_kind in PRIOR_SUBMISSION_ANSWER_NODES.items():
        for node in person_el.Elements(node_name):
            question_attr = node.Attribute("question")
            label = question_attr.Value if question_attr is not None else None
            if not label:
                continue
            value = xml_text(node, "Value") if answer_kind == "value_child" else node.Value
            if not value:
                continue
            if label in answers:
                skipped.append(label)
                continue
            answers[label] = value
    return answers, skipped


def join_field_values(pairs):
    """Join [(display_label_or_None, value), ...] into one readable answer string, e.g.
    [("Doctor", "Smith"), ("Phone", "555-1234")] -> "Doctor: Smith; Phone: 555-1234". A field with no
    display label (single-field types) contributes just its bare value. Returns None if empty."""
    parts = ["%s: %s" % (label, value) if label else value for label, value in pairs]
    return "; ".join(parts) if parts else None


def combined_value_from_element(person_el, fields):
    """Read one or more plain XML elements off person_el and join them into one readable answer
    string (see join_field_values)."""
    pairs = []
    for xml_property, display_label in fields:
        value = xml_text(person_el, xml_property)
        if value is not None:
            pairs.append((display_label, value))
    return join_field_values(pairs)


def simple_element_values_from_element(person_el):
    """The SIMPLE_ELEMENT_ASK_TYPES answers for one person block, keyed by ask_type."""
    values = {}
    for ask_type, (_q_type, _q_subtype, fields) in SIMPLE_ELEMENT_ASK_TYPES.items():
        value = combined_value_from_element(person_el, fields)
        if value is not None:
            values[ask_type] = value
    return values


def get_current_extra_values(member):
    """The simple_element answers from this person's CURRENT OnlineRegData -- these aren't covered by
    the OnlineRegQA view (see get_current_answers), so parse the XML directly."""
    if not member.OnlineRegData:
        return {}
    return simple_element_values_from_element(XElement.Parse(member.OnlineRegData))


# --- Answer history from OnlineOPRRegQA (primary source) --------------------------------------------
#
# Every enrollment writes one row per answered question into dbo.OnlineOPRRegQA (despite the "OPR"
# name this isn't limited to one-page registrations -- see OnlineRegPersonModel.Enroll.cs SaveAnswers):
# Type = the old Ask type, Question = the question's label, Answer = the answer as text, plus the
# CreatedDate and TranId of that enrollment. Unlike OrganizationMembers.OnlineRegData it is never
# overwritten, so each enrollment is its own dated submission with its own payment. It only exists for
# enrollments since mid-2022; older ones fall back to the XML sources (see find_prior_submissions).

# Types that record several rows, each with a fixed Question name rather than a label:
# ask_type -> [(Question name in OnlineOPRRegQA, display label in the combined answer), ...]
OPR_SIMPLE_FIELDS = {
    "AskAllergies": [("Allergies", None)],
    "AskCoaching": [("Interested in Coaching", None)],
    "AskTylenolEtc": [("Tylenol", "Tylenol"), ("Advil", "Advil"), ("Robitussin", "Robitussin"), ("Maalox", "Maalox")],
    "AskEmContact": [("Emcontact", "Contact"), ("Emphone", "Phone")],
    "AskInsurance": [("Insurance", "Carrier"), ("Policy", "Policy")],
    "AskDoctor": [("Doctor", "Doctor"), ("Docphone", "Phone")],
    "AskParents": [("Mname", "Mother"), ("Fname", "Father")],
    "AskChurch": [("Member", "Member here"), ("NoMember", "Not a member anywhere"),
                  ("ActiveInAnotherChurch", "Attends another church")],
}
# Types stored as one row whose Question is the ask's own label.
OPR_SINGLE_ROW_TYPES = ("AskSize", "AskGradeOptions", "AskRequest", "AskTickets", "AskCellPhone")
# Passport rows (stored encrypted) are never migrated, only the question. (AskPledge and AskSMS are never recorded in
# this table at all -- those come from the XML.)
OPR_SKIPPED_TYPES = ("AskPassport",)
# Types whose rows are a boolean per option; an option that wasn't chosen is just noise.
OPR_BOOLEAN_FIELD_TYPES = ("AskTylenolEtc", "AskChurch")


def submission_from_opr_rows(created, tran_id, rows):
    """Build one submission dict (the same shape find_prior_submissions returns) from the
    OnlineOPRRegQA rows written by a single enrollment."""
    answers = {}
    skipped = []
    simple_values = {}
    simple_rows = {}
    for row in rows:
        ask_type = row.Type
        answer = row.Answer
        if answer is None or answer == "" or ask_type in OPR_SKIPPED_TYPES:
            continue
        if ask_type in OPR_BOOLEAN_FIELD_TYPES and answer.lower() == "false":
            continue
        if ask_type in OPR_SIMPLE_FIELDS:
            simple_rows.setdefault(ask_type, {})[row.Question] = answer
        elif ask_type in OPR_SINGLE_ROW_TYPES:
            simple_values.setdefault(ask_type, answer)
        elif row.Question in answers:
            skipped.append(row.Question)
        else:
            answers[row.Question] = answer
    for ask_type, by_question in simple_rows.items():
        pairs = [(label, by_question[name]) for name, label in OPR_SIMPLE_FIELDS[ask_type] if name in by_question]
        if pairs:
            simple_values[ask_type] = join_field_values(pairs)

    return {"created": created, "tran_id": tran_id, "answers": answers, "skipped": skipped,
            "simple_values": simple_values}


def get_opr_submissions(org_id, people_id):
    """This person's enrollments in this Involvement from OnlineOPRRegQA, oldest first. Rows written
    by one enrollment share a CreatedDate and TranId, so that pair identifies a submission."""
    rows = q.QuerySql("""
        select Type, Question, Answer, CreatedDate, TranId
        from OnlineOPRRegQA
        where OrgId = %d and PeopleId = %d
        order by CreatedDate, Id
    """ % (org_id, people_id))
    groups = []
    index = {}
    for row in rows:
        key = (row.CreatedDate, row.TranId)
        if key not in index:
            index[key] = []
            groups.append((key, index[key]))
        index[key].append(row)
    return [submission_from_opr_rows(key[0], key[1], group_rows) for key, group_rows in groups]


def existing_transaction_ids(transaction_ids):
    """The subset of transaction_ids (in order, de-duplicated, zeros/None dropped) that actually exist --
    TranId in OnlineOPRRegQA isn't a foreign key, so don't assume it."""
    ids = []
    for transaction_id in transaction_ids:
        if transaction_id and int(transaction_id) not in ids:
            ids.append(int(transaction_id))
    if not ids:
        return []
    found = set(row.Id for row in q.QuerySql(
        "select Id from [Transaction] where Id in (%s)" % ",".join(str(i) for i in ids)))
    return [i for i in ids if i in found]


# --- Answer history from the XML sources (fallback for enrollments before OnlineOPRRegQA) ---------

def find_prior_submissions(org_id, people_id, exclude_datum_id, before=None):
    """Other COMPLETED dbo.RegistrationData rows for this Involvement whose submission included this
    person, besides the one their roster row currently points to (that one's answers are already
    covered by get_current_answers/get_current_extra_values). Each represents a separate historical
    registration session -- see the limitation note at the top of this script.
    If before is given (the date of this person's oldest OnlineOPRRegQA enrollment), only sessions
    stamped earlier than that are returned -- later ones are already covered by OnlineOPRRegQA, and
    would otherwise be migrated twice."""
    rows = q.QuerySql("""
        select Id as DatumId, Stamp, Data
        from RegistrationData
        where OrganizationId = %d and Completed = 1 and Id <> %d
    """ % (org_id, exclude_datum_id or 0))

    submissions = []
    for row in rows:
        if not row.Data:
            continue
        if before is not None and (row.Stamp is None or row.Stamp >= before):
            continue
        list_el = XElement.Parse(row.Data).Element("List")
        if list_el is None:
            continue
        for person_el in list_el.Elements("OnlineRegPersonModel"):
            pid_el = person_el.Element("PeopleId")
            if pid_el is not None and pid_el.Value == str(people_id):
                answers, skipped = answers_from_person_element(person_el)
                submissions.append({
                    "datum_id": row.DatumId, "created": row.Stamp, "answers": answers, "skipped": skipped,
                    "simple_values": simple_element_values_from_element(person_el),
                })
    return submissions


def get_transactions_for_datum(datum_id):
    """Transactions this RegistrationData submission produced (deposit + balance can mean more than
    one), via Transaction.DatumId -- the same column TouchPoint itself uses to trace a payment back
    to the registration session that created it."""
    return [row.Id for row in q.QuerySql("select Id from [Transaction] where DatumId = %d" % datum_id)]


def get_unaccounted_transactions(org_id, people_id, accounted_transaction_ids):
    """Transactions attributed to this person for this Involvement (via TransactionPeople) that
    aren't already explained by the current registration or any recovered prior submission -- e.g. a
    manual fee adjustment, or a payment whose submission record was deleted or predates both sources."""
    accounted = set(accounted_transaction_ids)
    rows = q.QuerySql("""
        select tp.Id as TransactionId
        from TransactionPeople tp
        where tp.OrgId = %d and tp.PeopleId = %d
    """ % (org_id, people_id))
    return [row.TransactionId for row in rows if row.TransactionId not in accounted]


def write_answers(reg_person_id, answers, simple_values, question_map, type_map, answer_kinds):
    """Record each recovered answer against its new RegQuestion. model.AddRegAnswer takes the answer
    as plain text and handles the JSON encoding itself."""
    for label, value in answers.items():
        reg_question_id = question_map.get(label)
        if reg_question_id:
            model.AddRegAnswer(reg_person_id, reg_question_id, prepare_answer(value, answer_kinds.get(reg_question_id)))
    for ask_type, value in simple_values.items():
        reg_question_id = type_map.get(ask_type)
        if reg_question_id:
            model.AddRegAnswer(reg_person_id, reg_question_id, prepare_answer(value, None, ask_type))


def migrate_member(org_id, member, question_map, type_map, answer_kinds, apply_changes):
    name = "%s %s" % (member.FirstName, member.LastName)
    status = status_for_member(member)
    email = member.EmailAddress or member.RegisterEmail
    created_date = member.EnrollmentDate
    completed_date = member.InactiveDate if status == 3 else member.EnrollmentDate

    # Answers for the CURRENT registration: from this person's newest OnlineOPRRegQA enrollment when
    # there is one; otherwise from the roster row's OnlineRegData XML (enrollments before mid-2022).
    xml_simple_values = get_current_extra_values(member)
    opr_submissions = get_opr_submissions(org_id, member.PeopleId)  # oldest first
    if opr_submissions:
        current = opr_submissions[-1]
        prior_opr_submissions = opr_submissions[:-1]
        answers, skipped_repeats = current["answers"], current["skipped"]
        current_simple_values = dict(current["simple_values"])
        for ask_type, value in xml_simple_values.items():  # e.g. pledge, SMS opt-in: never in OnlineOPRRegQA
            current_simple_values.setdefault(ask_type, value)
        answer_source = "OnlineOPRRegQA"
    else:
        current = None
        prior_opr_submissions = []
        answers, skipped_repeats = get_current_answers(org_id, member.PeopleId)
        current_simple_values = xml_simple_values
        answer_source = "OnlineRegData XML"
    unmatched = [label for label in answers if label not in question_map]

    print "  %s (PeopleId=%d): status=%d, %d answer(s) from %s (%d unmatched), fee=%s, paid=%s" % (
        name, member.PeopleId, status, len(answers), answer_source, len(unmatched), member.Amount, member.AmountPaid)
    if skipped_repeats:
        print "    NOTE: repeating question group(s) collapsed to one answer for: %s" % ", ".join(set(skipped_repeats))
    if unmatched:
        print "    WARNING: no matching RegQuestion for: %s" % ", ".join(unmatched)

    # Transactions: the roster row's own, plus the one its newest OnlineOPRRegQA enrollment recorded.
    current_transaction_ids = existing_transaction_ids(
        [member.TranId] + ([current["tran_id"]] if current else []))
    accounted_transaction_ids = list(current_transaction_ids)

    # One "extra" registration per earlier submission: first the earlier OnlineOPRRegQA enrollments,
    # then -- only for sessions that predate those -- RegistrationData XML ones; and finally whatever
    # payments still aren't explained become bare payment-only extras.
    extras = []
    for submission in prior_opr_submissions:
        transaction_ids = [t for t in existing_transaction_ids([submission["tran_id"]])
                           if t not in accounted_transaction_ids]
        accounted_transaction_ids.extend(transaction_ids)
        extras.append({"source": "OnlineOPRRegQA", "created": submission["created"],
                       "answers": submission["answers"], "skipped": submission["skipped"],
                       "simple_values": submission["simple_values"], "transaction_ids": transaction_ids})

    earliest_opr = opr_submissions[0]["created"] if opr_submissions else None
    for submission in find_prior_submissions(org_id, member.PeopleId, member.RegistrationDataId, earliest_opr):
        transaction_ids = [t for t in get_transactions_for_datum(submission["datum_id"])
                           if t not in accounted_transaction_ids]
        accounted_transaction_ids.extend(transaction_ids)
        extras.append({"source": "RegistrationData XML", "created": submission["created"],
                       "answers": submission["answers"], "skipped": submission["skipped"],
                       "simple_values": submission["simple_values"], "transaction_ids": transaction_ids})
    for transaction_id in get_unaccounted_transactions(org_id, member.PeopleId, accounted_transaction_ids):
        extras.append({"source": "payment only", "created": None, "answers": {}, "skipped": [],
                       "simple_values": {}, "transaction_ids": [transaction_id]})

    for extra in extras:
        recovered = len(extra["answers"]) + len(extra["simple_values"])
        extra_unmatched = [label for label in extra["answers"] if label not in question_map]
        print "    prior submission (%s): %d recovered answer(s), %d transaction(s)%s" % (
            extra["source"], recovered, len(extra["transaction_ids"]), "" if recovered else " (no answers recovered)")
        if extra["skipped"]:
            print "      NOTE: repeating question group(s) collapsed to one answer for: %s" % ", ".join(set(extra["skipped"]))
        if extra_unmatched:
            print "      WARNING: no matching RegQuestion for: %s" % ", ".join(extra_unmatched)

    if not apply_changes:
        return

    registration_id = model.CreateRegistration(org_id, member.PeopleId, created_date, completed_date)
    reg_person_id = model.AddRegPerson(registration_id, member.PeopleId, member.FirstName, member.LastName,
                                        email, status, completed_date, member.Amount, member.AmountPaid or 0)
    write_answers(reg_person_id, answers, current_simple_values, question_map, type_map, answer_kinds)
    for transaction_id in current_transaction_ids:
        model.LinkTransactionToRegistration(transaction_id, registration_id)

    for extra in extras:
        extra_created = extra["created"] or created_date
        extra_completed = extra["created"] or completed_date
        extra_registration_id = model.CreateRegistration(org_id, member.PeopleId, extra_created, extra_completed)
        extra_reg_person_id = model.AddRegPerson(extra_registration_id, member.PeopleId, member.FirstName,
                                                  member.LastName, email, status)
        write_answers(extra_reg_person_id, extra["answers"], extra["simple_values"], question_map, type_map,
                      answer_kinds)
        for transaction_id in extra["transaction_ids"]:
            model.LinkTransactionToRegistration(transaction_id, extra_registration_id)



# --- What's different in the new paradigm (printed with every preview/apply) ------------------------

# Old ask types whose branching (show different follow-up questions per choice) isn't reconstructed.
BRANCHING_ASK_TYPES = ("AskDropdownWithCondition", "AskRadioCondition",
                       "AskDropdownWithRedirect", "AskRadioRedirect")
# Old ask types that saved their answer onto the person's own records when submitted, and whose
# matching new question types also update the person (medications, shirt size, grade, parents, passport --
# see RegistrationsService.SaveQuestionAnswers) when a FUTURE submission is made. Migrated history never
# touches anyone's records.
PROFILE_UPDATING_ASK_TYPES = ("AskTylenolEtc", "AskSize", "AskGradeOptions", "AskParents", "AskPassport")


def labels_for(questions, predicate, limit=8):
    labels = [question["label"] for question in questions if predicate(question)]
    shown = ", ".join(repr(label) for label in labels[:limit])
    return shown + (", and %d more" % (len(labels) - limit) if len(labels) > limit else ""), len(labels)


def print_differences(questions):
    """Warn about the places where the new Registration Form works differently from the old one, so
    the preview shows them before anything is applied. Always-true points come first; the rest only
    appear when this Involvement actually has the kind of question they're about."""
    print "=== Differences from the old registration -- please read ==="
    print "  * History only: past registrants' sub-groups, extra values and profile fields are NOT changed."
    print "    Their answers are recorded on their Registrations, but nobody's current state is touched --"
    print "    including cell phone, SMS opt-in and grade, which become answers rather than profile updates."

    shown, count = labels_for(questions, lambda x: x["save_as"] == SAVE_AS_SUBGROUP)
    if count:
        print "  * %d question(s) will put people in a sub-group named for their choice when they submit the" % count
        print "    NEW form (as before). Migrated registrants are not added to or removed from any sub-group: %s" % shown

    shown, count = labels_for(questions, lambda x: x["save_as"] == SAVE_AS_EXTRA_VALUE)
    if count:
        print "  * %d question(s) saved to extra values in the old form and still will, but the new form does it" % count
        print "    differently: a radio/dropdown choice is stored as <choice> = <the option's value>, where the old form"
        print "    stored <choice> = true; checkboxes store text where the old form stored a true/false; the new form"
        print "    doesn't clear the other choices' extra values when someone changes their answer; and it writes to"
        print "    the involvement member as well as the person. Reports/queries on these values may need updating: %s" % shown

    shown, count = labels_for(questions, lambda x: any("Limit" in option for option in x["options"]))
    if count:
        print "  * Option limits were carried over for %d question(s): %s. The new form counts sub-group members" % (count, shown)
        print "    for sub-group questions, and otherwise counts existing answers (which now include migrated history)."

    shown, count = labels_for(questions, lambda x: x["old_type"] in BRANCHING_ASK_TYPES)
    if count:
        print "  * %d question(s) had choice-dependent follow-ups or redirects in the old form. Their choices were" % count
        print "    migrated as a plain list; the branching was NOT rebuilt (see RegQuestionOption.SkipToId): %s" % shown

    shown, count = labels_for(questions, lambda x: x["old_type"] in PROFILE_UPDATING_ASK_TYPES)
    if count:
        print "  * %d question(s) save their answer onto the person's own records (medications, shirt size, grade," % count
        print "    parents, passport). The new form does the same for FUTURE submissions: %s" % shown

    shown, count = labels_for(questions, lambda x: x["old_type"] == "AskPassport")
    if count:
        print "  * Passport: the question was migrated, but NO passport details were -- not from the current or any"
        print "    earlier registration. Registrants will need to enter them again: %s" % shown

    shown, count = labels_for(questions, lambda x: x["old_type"] == "AskDocuments")
    if count:
        print "  * Document questions: recovered answers are filed under each document's name, which may not match"
        print "    the question's label, so some may be reported as 'no matching RegQuestion': %s" % shown

    shown, count = labels_for(questions, lambda x: x["question_type"] == 3 and "ask_type" not in x)
    if count:
        print "  * Checkbox answers were recorded as comma-separated text and are split back into choices using the"
        print "    question's options. Spot-check these: %s" % shown

    print "  * Each earlier enrollment becomes its own Registration. Enrollments from before mid-2022 are recovered"
    print "    from other stored data where possible; otherwise only the payment is kept (no answers)."


# --- Orchestration -----------------------------------------------------------------------------

def run(org_id, apply_changes):
    settings_xml = get_legacy_settings_xml(org_id)

    print "=== Settings ==="
    settings = translate_settings(org_id, settings_xml)
    if settings:
        for column, value in settings.items():
            print "  %s = %r" % (column, value)
        if apply_changes:
            model.UpdateOrganization(org_id, settings)
    else:
        print "  nothing to translate"

    print "=== Questions ==="
    questions, unhandled_types = parse_ask_items(settings_xml)
    question_map, type_map, answer_kinds = migrate_questions(org_id, questions, apply_changes)
    if unhandled_types:
        print "  SKIPPED (add by hand with model.AddRegQuestion): %s" % ", ".join(set(unhandled_types))

    print_differences(questions)

    print "=== Registrations, answers, and payments ==="
    roster = list(get_roster(org_id))
    print "  %d roster member(s)" % len(roster)
    for member in roster:
        migrate_member(org_id, member, question_map, type_map, answer_kinds, apply_changes)

    if apply_changes:
        print "=== Applied. Run ValidateRegistrationMigration.sql next, then call " \
              "model.SetOrgRegistrationType(%d, %d) once you're satisfied with the result. ===" % (org_id, REGISTRATION_FORM_TYPE)
    else:
        print "=== Preview only -- pass &apply=1 to write these values. ==="


if Data.orgid == '':
    print "Pass ?orgid=NNNN (and optionally &apply=1) to migrate that Involvement's registration data."
else:
    run(int(Data.orgid), Data.apply == '1')
