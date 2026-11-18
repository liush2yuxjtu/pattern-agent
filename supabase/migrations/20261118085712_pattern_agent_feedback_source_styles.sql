create view pattern_agent.feedback_by_source_style with (security_invoker = true) as
select
    review.source_code as source_key,
    review.source_title,
    review.product_id as style_key,
    '商品 ' || review.product_id as style_title,
    'dataset'::text as feedback_kind,
    review.garment,
    review.signal_id as feedback_id,
    review.review_id,
    review.part_code,
    review.part,
    review.evidence,
    review.candidate,
    review.measurement,
    review.preserve,
    review.source_url,
    review.archive_filename,
    review.source_index,
    null::text as locator
from pattern_agent.search_feedback as review
union all
select
    'publisher:' || feedback.publisher,
    feedback.publisher,
    btrim(feedback.garment),
    btrim(feedback.garment),
    'curated',
    feedback.garment,
    feedback.feedback_id,
    feedback.feedback_id,
    feedback.part_code,
    part.label,
    feedback.evidence,
    feedback.candidate,
    feedback.measurement,
    feedback.preserve,
    feedback.source_url,
    null::text,
    null::integer,
    feedback.locator
from pattern_agent.curated_feedback as feedback
join pattern_agent.feedback_parts as part using (part_code);

create view pattern_agent.feedback_style_counts with (security_invoker = true) as
select
    source_key, source_title, style_key, style_title, feedback_kind,
    count(distinct review_id) as review_count,
    count(*) as feedback_count
from pattern_agent.feedback_by_source_style
group by source_key, source_title, style_key, style_title, feedback_kind;

revoke all on pattern_agent.feedback_by_source_style, pattern_agent.feedback_style_counts
from public, anon, authenticated;
