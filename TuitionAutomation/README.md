# Tuition Automation

This is a tool intended for billing monthly tuition for students in our Preschool program.  This is a function
that TouchPoint is *definitely not* built for, so while this solution is  **NOT** an ideal solution, it is a viable
solution and provides the level of flexibility we need.  However, if you want a more capable system, you should probably
look to a true Learning/School/Preschool management system.

## Limitations
- **Cannot set up automatic recurring payments.**  (That is, payments without user intervention.)  That's just not a thing that TouchPoint can currently do.
- **Sometimes requires a separate PayLink for each child.**  If parents register multiple children at the same time through a TouchPoint registration, they can share a paylink.  Otherwise, you'll end up with a separate paylink per child.

## Features
- **Automatic Discounts** based on attributes in the database.  For example, we have a discount for church members.  If parents become members during the school year, the discount automatically starts applying once they become members.
- **Manual Override option** for students who may be on scholarship or financial aid.
- **Unified accounts** for each child across related programs, so the main program and aftercare can be billed/paid together.
- **Automated-ish Billing emails** with the account history and balance.

## Setup
1.  Download the TuitionAutomation zip file from the releases and install it at `mychurch.tpsdb.com/InstallPyScriptProject`.
    This will install the scripts, but you will need to customize them.
2.  Create an involvement which will be the "payment involvement" in the rest of this documentation.  If you want families to register online, including paying a deposit, this is the involvement where you should put the registration form.  The script assumes that the deposit amount 
    is the same as one month.  If this is not the case (and especially if you allow offline registration), you may need to adjust the script. 
3.  Create involvements for each class (hereafter, "class involvements").  You will need to add the students as members of these involvements.  We recommend also adding the teachers as leaders, so they can take attendance.   The class involvements can be child involvements of
    the payment involvement, but this is not required. Take note of the Involvement IDs for all of these involvements. 
4.  Go to Special Content > Python and edit the TuitionAutomation script. Towards the top, you'll see a few variables that you'll need to customize:
    ```python
    paymentOrgId = 51
    minTransactionId = 17000
    ```
    The `paymentOrgId` is the Involvement ID of the payment involvement.

    The `minTransactionId` is a means of filtering out older transactions, which is particularly useful if you reuse involvements year to year.  (We recommend alternating involvements year to year, so one involvement is the current year, while the other is for next year.  More on transitioning between years is below.)

    Then, there's a section where each class's parameters are spelled out:
    ```python
    orgs = [
        {
            'id': 209,
            'name': "2-Year-Old",
            'base': 332
        },
        {
            'id': 215,
            'name': "Afternoon - Mon",
            'base': 40,
            'payPer': "meeting",
            'discounts': False
        },
        ...
    ]
    ```
    Each set of {} brackets goes with a single class.  You'll need one of those for each class involvement.  **Important**:
    billing is processed **in order** along this list, starting at the top.  So, if you want to have a "younger sibling"
    discount, make sure you put these in order with older classes listed first.

    `id` is the Involvement ID of the class involvement.

    `name` is the name of the Involvement, as you want it to appear on billing statements and transactions.

    `base` is the amount of tuition to charge.  By default, this is per-month.

    `payPer` allows for switching to per-meeting billing, rather than per-month.  If you're sticking with the default of per-month, you can remove this field.  (Our aftercare program is billed per-meeting for which the student is enrolled.)

    `discounts` can be set false to disallow discounts, such as the sibling discount and church member discount. (Our aftercare program does not allow discounts.)
5.  Once you've customized the script, you can run it from the Python page.  This will assess the tuition for each student in each class involvement.  This initial run will make sure all students enrolled in the classes are also members of the payment involvement. 
6.  If you need to provide special discounts or scholarships, you can do so by adding a note to the student's involvement membership **in the class involvement**.  To do this, go to the class involvement > People and click the pencil icon for the student.  Then, on the Extra Value tab, add an Extra Value of type "Integer" named "Tuition" with the value being the amount of tuition to bill, replacing the amount defined in the script as described above.  Only whole-dollar positive amounts are supported.

## Usage
Once the setup steps are complete, navigate to /PyScript/TuitionAutomation from which you'll be able to access most of
the features available to you.

## Between School Years

You can only handle one school year at a time in a payment involvement.

We have two payment involvements, one for the current year and one for the next year.  This allows us to transition between years without losing the history of the previous year. 
Mid-way through the year, when we open registration for the next year, we configure registration in the non-current payment involvement, where parents can enroll and pay the deposits for their children.  The deposit amounts are just fees in the registration and are handled in the normal way.  If you don't want to charge fees at enrollment, you don't have to.

During the summer:
- Update class involvements to reflect the new class lists. Make sure teachers are added as leaders in the involvements.
- Change the Payment Involvement ID to a different one from the previous year. 
- If needed, update the minimum transaction ID in the script to filter out old transactions.
- Update the script to reflect the new class involvements (if changed) and tuition amounts.
- ALWAYS double-check the assessed amounts BEFORE applying them to accounts.

