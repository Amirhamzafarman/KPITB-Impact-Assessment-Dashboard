-- =============================================================================
-- SQL Script for arms_denormal Table (PostgreSQL)
-- Database: postgres / rtsdash
-- Schema: public
-- Total Columns: 86
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. Table Schema Definition (DDL)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.arms_denormal (
    id bigint PRIMARY KEY,
    arms_license_id integer,
    arms_license_uuid varchar(255),
    applicant_id bigint,
    applicant_cnic varchar(255),
    applicant_dob date,
    applicant_gender_id smallint,
    applicant_gender_title varchar(255),
    application_type_id integer,
    application_type_title varchar(255),
    applicant_type_id integer,
    applicant_type_title varchar(255),
    applicability_type_id integer,
    applicability_type_title varchar(255),
    weapon_restriction_id integer,
    weapon_restriction_title varchar(255),
    weapon_type_id integer,
    weapon_type_title varchar(255),
    bore_type_id integer,
    bore_type_title varchar(255),
    cartridge_id varchar(255),
    application_reason_id smallint,
    application_reason_title varchar(255),
    profession_id integer,
    profession_title varchar(255),
    district_id_applied_from integer,
    district_id_applied_from_title varchar(255),
    current_province_id integer,
    current_province_title varchar(255),
    current_district_id integer,
    current_district_title varchar(255),
    permanent_province_id integer,
    permanent_province_title varchar(255),
    permanent_district_id integer,
    permanent_district_title varchar(255),
    is_nadra_verified smallint,
    is_police_verified smallint,
    is_retainer_selected smallint,
    is_retainer_nadra_verified smallint,
    is_retainer_police_verified smallint,
    retainer_cnic varchar(255),
    application_created_at timestamp without time zone,
    district_id integer,
    approved_by_district_id integer,
    approved_by_user_id integer,
    dc_user_id integer,
    so_user_id integer,
    is_govt_employee smallint,
    is_gop_verified smallint,
    is_lea_personnel smallint,
    lea_type_id integer,
    lea_type_title varchar(255),
    is_eligible_by_dc smallint,
    is_eligible_by_so smallint,
    is_rejected smallint,
    is_deficient smallint,
    is_payment_done smallint,
    total_amount real,
    payment_created_at timestamp without time zone,
    payment_paid_at timestamp without time zone,
    is_printed smallint,
    is_printed_batch_received smallint,
    is_printed_card_received smallint,
    print_queued_at timestamp without time zone,
    print_completed_at timestamp without time zone,
    print_dispatched_at timestamp without time zone,
    print_batch_received_at timestamp without time zone,
    print_card_received_at timestamp without time zone,
    print_dc_user_id integer,
    is_application_closed smallint,
    application_closed_at timestamp without time zone,
    dc_assigned_user_id integer,
    dc_assigned_datetime timestamp without time zone,
    dc_approved_user_id integer,
    dc_approved_datetime timestamp without time zone,
    so_assigned_datetime timestamp without time zone,
    so_approved_datetime timestamp without time zone,
    applicant_nadra_verified_at timestamp without time zone,
    retainer_nadra_verified_at timestamp without time zone,
    applicant_nadra_tracking_id varchar(255),
    retainer_nadra_tracking_id varchar(255),
    applicant_license_id bigint,
    is_application_completed smallint,
    applicant_name varchar(255),
    applicant_father_name varchar(255),
    applicant_contact_no varchar(255)
);

-- -----------------------------------------------------------------------------
-- 2. Helpful Index Options for Performance
-- -----------------------------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_arms_denormal_applicant_cnic ON public.arms_denormal(applicant_cnic);
CREATE INDEX IF NOT EXISTS idx_arms_denormal_district_id ON public.arms_denormal(district_id);
CREATE INDEX IF NOT EXISTS idx_arms_denormal_application_created_at ON public.arms_denormal(application_created_at);

-- -----------------------------------------------------------------------------
-- 3. Verification & Summary Queries
-- -----------------------------------------------------------------------------

-- Query 3.1: Check Total Row Count
SELECT COUNT(*) AS total_rows FROM public.arms_denormal;

-- Query 3.2: Check Primary Key Min/Max ID & Total Count
SELECT 
    COUNT(*) AS total_rows,
    MIN(id)  AS min_id,
    MAX(id)  AS max_id
FROM public.arms_denormal;

-- Query 3.3: Inspect Column Structure & Data Types
SELECT 
    column_name, 
    data_type 
FROM information_schema.columns 
WHERE table_schema = 'public' 
  AND table_name = 'arms_denormal'
ORDER BY ordinal_position;

-- Query 3.4: Sample Top 10 Records
SELECT 
    id, 
    arms_license_id, 
    applicant_cnic, 
    applicant_name, 
    applicant_father_name, 
    weapon_type_title, 
    bore_type_title, 
    application_created_at 
FROM public.arms_denormal 
ORDER BY id 
LIMIT 10;
