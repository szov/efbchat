from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from server import models


async def get_or_create_user(db: AsyncSession, device_id: str) -> models.User:
    """
    Returns the user if they exist, otherwise creates and returns them.
    :param db:
    :param device_id:
    :return: models.User
    """
    user = await db.execute(
        select(models.User)
        .where(models.User.device_id == device_id)
    )
    user = user.scalar_one_or_none()

    if not user:
        user = models.User(
            device_id=device_id
        )
        db.add(user)
        await db.commit()

    return user


async def add_match(
        db: AsyncSession,
        user1: models.User,
        user2: models.User,
        match_id: str,
        left_name: str,  # NEW
        right_name: str,  # NEW
) -> None:
    """
    Add a match between two users into the database.
    :param db:
    :param user1:
    :param user2:
    :param match_id:
    :param left_name:
    :param right_name:
    :return:
    """
    match = models.Match(
        match_id=match_id,
        user_a_id=user1.user_id,
        user_b_id=user2.user_id,
        left_name=left_name,
        right_name=right_name,
    )
    db.add(match)
    await db.commit()


async def add_message(db: AsyncSession, match_id: str, user: models.User, content: str) -> models.Message:
    """
    Stores a message in the database
    :param db:
    :param match_id:
    :param user:
    :param content:
    :return:
    """
    msg = models.Message(
        match_id=match_id,
        sender_id=user.user_id,
        content=content
    )
    db.add(msg)
    await db.commit()
    return msg


async def get_history(db: AsyncSession, user1: models.User, user2: models.User) -> list[dict]:
    """
    Returns the message history between two users
    :param db:
    :param user1:
    :param user2:
    :return: The list of all their messages
    """

    # Find all matches played between both opponents
    matches = await db.execute(
        select(models.Match.match_id)
        .where(
            ((models.Match.user_a_id == user1.user_id) & (models.Match.user_b_id == user2.user_id)) |
            ((models.Match.user_a_id == user2.user_id) & (models.Match.user_b_id == user1.user_id))
        )
    )

    # Storing match_ids
    match_ids: list[models.Message] = [m[0] for m in matches.all()]
    messages = await db.execute(
        select(models.Message)
        .where(models.Message.match_id.in_(match_ids))
        .order_by(models.Message.ts)
    )

    result: list[dict] = []
    for msg in messages.scalars().all():
        result.append({
            "sender": "You" if msg.sender_id == user1.user_id else user2.username,
            "content": msg.content,
            "id": msg.msg_id,
            "ts": msg.ts
        })

    return result


async def infer_name(db: AsyncSession, device_id: str, names: set[str]) -> str | None:
    """
    Check anonymity rule:
    If a user has no previous opponents, they will remain anonymous
    Else if a user has one previous opponent, and they are playing the same one once more, they will remain anonymous
    Else if a use has one previous opponent, and they are playing an unplayed second one, their username is confirmed
    :param db:
    :param device_id:
    :param names:
    :return:
    """

    # Fetch user row
    user: models.User | None = (await db.execute(
        select(models.User)
        .where(models.User.device_id == device_id)
    )).scalar_one_or_none()
    if not user:
        return None

    # Fetch and store all matches where the user has participated
    matches = (await db.execute(
        select(models.Match).where(
            (models.Match.user_a_id == user.user_id) |
            (models.Match.user_b_id == user.user_id)
        )
    )).scalars().all()

    # Store all names found in the matches variable (using a set() for no duplicate entries)
    all_names = set()
    for m in matches:
        all_names.add(m.left_name)
        all_names.add(m.right_name)

    # Intersect all names found in all previous matches and the two names in this match
    intersection = names & all_names

    # if the intersections results in one name (the user calling the function), then their names will be placed in the database.
    if len(intersection) == 1:
        name = intersection.pop()
        user.username = name
        await db.commit()
        return name

    return None


async def fetch_contacts(db: AsyncSession, device_id: str) -> list[dict]:
    """
    fetches all previous chats/contacts for the user
    :param db:
    :param device_id:
    :return: All previous contacts, sorted by most recent message
    """
    # Fetch the user row
    my_user = (await db.execute(
        select(models.User)
        .where(models.User.device_id == device_id)
    )).scalar_one_or_none()

    if not my_user:
        return []

    # Find and store all matches where the user has participated
    matches = (await db.execute(
        select(models.Match)
        .where(
            (models.Match.user_a_id == my_user.user_id) |
            (models.Match.user_b_id == my_user.user_id)

        )
    )).scalars().all()

    # Find all previous opponents (or chats i guess) and store them alongside their respective match_ids
    partner_matches: dict[str, list[str]] = {}
    for m in matches:
        pid = m.user_b_id if m.user_a_id == my_user.user_id else m.user_a_id
        partner_matches.setdefault(pid, []).append(m.match_id)

    if not partner_matches:
        return []

    # Fetch previous opponents usernames
    partner_users = await db.execute(
        select(models.User).where(models.User.user_id.in_(partner_matches.keys()))
    )
    # Maps {user_id: models.User object}
    users_map = {u.user_id: u for u in partner_users.scalars().all()}

    # Find all match_ids
    all_mids = [mid for mids in partner_matches.values() for mid in mids]

    # Fetch ALL messages from ALL shared matches in one shot
    all_msgs = await db.execute(
        select(models.Message)
        .where(models.Message.match_id.in_(all_mids))
        .order_by(models.Message.ts.desc())
    )
    all_msgs = all_msgs.scalars().all()

    # Latest message per partner (iterate once, messages already DESC)
    latest: dict[str, models.Message] = {}
    for msg in all_msgs:
        for pid, mids in partner_matches.items():
            if msg.match_id in mids and pid not in latest:
                latest[pid] = msg

    result = []
    for pid, mids in partner_matches.items():
        u = users_map.get(pid)
        if not u:
            continue
        last = latest.get(pid)
        result.append({
            "user_id": u.user_id,
            "username": u.username,
            "last_message": last.content if last else None,
            "last_ts": last.ts if last else None,
            "match_count": len(mids),
        })

    result.sort(key=lambda x: x["last_ts"] or 0, reverse=True)
    return result
