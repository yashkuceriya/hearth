"""Tests for the Data Rights Manager."""

from brain.ingestion.data_rights import DataRightsManager, DataSource, DataLicense


class TestDataRightsManager:
    def setup_method(self):
        self.manager = DataRightsManager()

    def test_tcad_single_lookup_allowed(self):
        result = self.manager.check_access(
            source=DataSource.TCAD,
            market="travis_county",
            use_case="single_property_lookup",
        )
        assert result.allowed is True
        assert "no_bulk_transfer" in result.restrictions

    def test_tcad_bulk_transfer_denied(self):
        result = self.manager.check_access(
            source=DataSource.TCAD,
            market="travis_county",
            use_case="bulk_export",
        )
        assert result.allowed is False
        assert "bulk_export" in result.denial_reason

    def test_mls_no_license_denied(self):
        result = self.manager.check_access(
            source=DataSource.MLS,
            market="austin",
            use_case="production_listing",
        )
        assert result.allowed is False

    def test_reso_dev_reference_allowed(self):
        result = self.manager.check_access(
            source=DataSource.RESO_REFERENCE,
            market="austin",
            use_case="development",
        )
        assert result.allowed is True
        assert "not_for_production" in result.restrictions

    def test_custom_license_registration(self):
        self.manager.register_license(DataLicense(
            license_id="custom-mls-prod",
            source=DataSource.MLS,
            market="austin",
            allowed_use_cases=["production_listing", "valuation_input"],
            restrictions=["display_attribution_required"],
        ))
        result = self.manager.check_access(
            source=DataSource.MLS,
            market="austin",
            use_case="production_listing",
            license_id="custom-mls-prod",
        )
        assert result.allowed is True

    def test_rate_limiting(self):
        # TCAD has 60/hour limit
        for _ in range(60):
            result = self.manager.check_access(
                source=DataSource.TCAD,
                market="travis_county",
                use_case="single_property_lookup",
            )
            assert result.allowed is True

        # 61st should be denied
        result = self.manager.check_access(
            source=DataSource.TCAD,
            market="travis_county",
            use_case="single_property_lookup",
        )
        assert result.allowed is False
        assert "Rate limit" in result.denial_reason

    def test_access_log_recorded(self):
        self.manager.check_access(
            source=DataSource.TCAD,
            market="travis_county",
            use_case="single_property_lookup",
        )
        log = self.manager.get_access_log()
        assert len(log) >= 1
        assert log[-1].allowed is True
        assert log[-1].source == DataSource.TCAD


class TestDataRightsManagerValuationUseCase:
    def test_valuation_input_allowed_for_tcad(self):
        manager = DataRightsManager()
        result = manager.check_access(
            source=DataSource.TCAD,
            market="travis_county",
            use_case="valuation_input",
        )
        assert result.allowed is True
