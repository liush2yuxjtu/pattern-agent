-- Project collaborators query this schema through the Supabase connection.
create schema pattern_agent;

create table pattern_agent.cad_assets (
    asset_id text primary key,
    title text not null,
    original_name text not null,
    formats text[] not null check (
        cardinality(formats) > 0 and formats <@ array['DXF', 'PRJ', 'ZPRJ', 'ZPROJ', 'ZPAC']
    ),
    garment text,
    source_code text not null,
    source_name text not null,
    source_url text not null,
    source_member text,
    role text,
    audit text not null,
    bytes bigint check (bytes > 0),
    sha256 text unique check (sha256 ~ '^[0-9a-f]{64}$'),
    check ((bytes is null) = (sha256 is null))
);

create table pattern_agent.cad_drive_locations (
    asset_id text primary key references pattern_agent.cad_assets (asset_id),
    file_id text not null,
    archive_member text
);

create table pattern_agent.feedback_sources (
    source_code text primary key,
    title text not null,
    source_url text not null,
    license text not null,
    archive_filename text not null,
    archive_sha256 text not null check (archive_sha256 ~ '^[0-9a-f]{64}$'),
    citation_url text,
    counts jsonb not null
);

create table pattern_agent.feedback_parts (
    part_code text primary key,
    label text not null,
    measurement text not null,
    preserve text not null
);

create table pattern_agent.feedback_actions (
    action_code text primary key,
    label text not null
);

create table pattern_agent.feedback_reviews (
    review_id text primary key,
    source_code text not null references pattern_agent.feedback_sources (source_code),
    source_index integer not null check (source_index >= 0),
    product_id text not null,
    garment text not null,
    source_garment text,
    rating text,
    unique (source_code, source_index)
);

create table pattern_agent.feedback_signals (
    signal_id text primary key,
    review_id text not null references pattern_agent.feedback_reviews (review_id),
    part_code text not null references pattern_agent.feedback_parts (part_code),
    action_code text not null references pattern_agent.feedback_actions (action_code),
    evidence text not null,
    unique (review_id, part_code, action_code)
);

create table pattern_agent.curated_feedback (
    feedback_id text primary key,
    part_code text not null references pattern_agent.feedback_parts (part_code),
    garment text not null,
    publisher text not null,
    locator text not null,
    source_url text not null,
    evidence text not null,
    candidate text not null,
    measurement text not null,
    preserve text not null
);

create table pattern_agent.design_intents (
    intent_id text primary key,
    feedback_id text not null unique references pattern_agent.curated_feedback (feedback_id),
    region text not null,
    request text not null,
    measurement_inputs text not null,
    preserve text not null,
    target jsonb,
    state text not null
);

create index feedback_signals_part_review on pattern_agent.feedback_signals (part_code, review_id);
create index feedback_reviews_garment on pattern_agent.feedback_reviews (garment, review_id);
create index curated_feedback_part on pattern_agent.curated_feedback (part_code, garment);

create view pattern_agent.search_feedback with (security_invoker = true) as
select
    signal.signal_id, review.review_id, review.garment, review.source_code,
    review.source_index, review.product_id, signal.part_code, part.label as part,
    signal.action_code, action.label as candidate, signal.evidence, part.measurement,
    part.preserve, source.title as source_title, source.source_url, source.archive_filename
from pattern_agent.feedback_signals as signal
join pattern_agent.feedback_reviews as review using (review_id)
join pattern_agent.feedback_parts as part using (part_code)
join pattern_agent.feedback_actions as action using (action_code)
join pattern_agent.feedback_sources as source using (source_code);

alter table pattern_agent.cad_assets enable row level security;
alter table pattern_agent.cad_drive_locations enable row level security;
alter table pattern_agent.feedback_sources enable row level security;
alter table pattern_agent.feedback_parts enable row level security;
alter table pattern_agent.feedback_actions enable row level security;
alter table pattern_agent.feedback_reviews enable row level security;
alter table pattern_agent.feedback_signals enable row level security;
alter table pattern_agent.curated_feedback enable row level security;
alter table pattern_agent.design_intents enable row level security;

revoke all on schema pattern_agent from public, anon, authenticated;
revoke all on all tables in schema pattern_agent from public, anon, authenticated;
