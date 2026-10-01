import unittest
import os
import tempfile
import pandas as pd
from models import Company
from processors.normalize import clean_url, format_website, clean_linkedin, normalize_funding, normalize_company
from processors.deduplicate import simplify_name, merge_companies, deduplicate_companies
from fetchers import get_all_fetchers
from exporters.excel import export_to_excel

class TestStartupFinderPipeline(unittest.TestCase):
    
    def test_url_cleaning(self):
        self.assertEqual(clean_url("https://www.example.com/"), "example.com")
        self.assertEqual(clean_url("http://example.com"), "example.com")
        self.assertEqual(clean_url("  example.com/  "), "example.com")
        self.assertEqual(format_website("example.com"), "https://example.com")

    def test_linkedin_cleaning(self):
        self.assertEqual(clean_linkedin("linkedin.com/company/my-startup"), "https://linkedin.com/company/my-startup")
        self.assertEqual(clean_linkedin("https://www.linkedin.com/company/my-startup/"), "https://linkedin.com/company/my-startup/")

    def test_funding_normalization(self):
        self.assertEqual(normalize_funding("$1,500,000"), "$1.5M")
        self.assertEqual(normalize_funding("8.5M"), "$8.5M")
        self.assertEqual(normalize_funding("120000"), "$120K")
        self.assertEqual(normalize_funding("Unknown"), "Unknown")
        self.assertEqual(normalize_funding("5B"), "$5B")

    def test_company_normalization(self):
        c = Company(
            name="my-startup llc",
            website="http://my-startup.com",
            country="saudi arabia",
            city="riyadh",
            industry="ai tech",
            category="AI",
            description="An AI startup",
            founding_year=2024,
            employee_count=10,
            funding_stage="seed stage",
            total_funding="500000",
            linkedin="linkedin.com/company/my-startup",
            email="CONTACT@my-startup.com",
            technologies=["python", "React", "react"],
            source="Test"
        )
        norm = normalize_company(c)
        self.assertEqual(norm.name, "My-Startup LLC")
        self.assertEqual(norm.website, "https://my-startup.com")
        self.assertEqual(norm.country, "Saudi Arabia")
        self.assertEqual(norm.city, "Riyadh")
        self.assertEqual(norm.funding_stage, "Seed Stage")
        self.assertEqual(norm.total_funding, "$500K")
        self.assertEqual(norm.email, "contact@my-startup.com")
        self.assertEqual(norm.technologies, ["Python", "React"])

    def test_name_simplification(self):
        self.assertEqual(simplify_name("My Startup LLC"), "mystartup")
        self.assertEqual(simplify_name("The Super Cool Technologies Group"), "thesupercool")

    def test_deduplication_and_merge(self):
        c1 = Company(
            name="Tamara",
            website="https://tamara.co",
            country="Saudi Arabia",
            description="Buy now pay later.",
            category="FinTech",
            founding_year=2020,
            funding_stage="Growth",
            total_funding="Unknown",
            source="SourceA"
        )
        c2 = Company(
            name="Tamara Co",
            website="https://tamara.co",
            country="Saudi Arabia",
            description="Tamara is a leading BNPL solution in Saudi.",
            category="FinTech",
            employee_count=500,
            funding_stage="Series C",
            total_funding="$440M",
            linkedin="https://linkedin.com/company/playtamara",
            source="SourceB"
        )
        
        merged_list = deduplicate_companies([c1, c2])
        self.assertEqual(len(merged_list), 1)
        merged = merged_list[0]
        self.assertEqual(merged.name, "Tamara Co")  # Longest name
        self.assertEqual(merged.description, "Tamara is a leading BNPL solution in Saudi.")  # Longest description
        self.assertEqual(merged.employee_count, 500)
        self.assertEqual(merged.funding_stage, "Series C")  # Specific stage over Unknown
        self.assertEqual(merged.total_funding, "$440M")  # Specific funding over Unknown
        self.assertEqual(merged.linkedin, "https://linkedin.com/company/playtamara")
        self.assertEqual(merged.source, "SourceA, SourceB")  # Merged sources

    def test_dynamic_fetcher_discovery(self):
        fetchers = get_all_fetchers()
        # Verify that all 6 fetchers are successfully discovered
        fetcher_names = [f.name for f in fetchers]
        self.assertIn("YC", fetcher_names)
        self.assertIn("GitHub", fetcher_names)
        self.assertIn("Google", fetcher_names)
        self.assertIn("Crunchbase", fetcher_names)
        self.assertIn("Wellfound", fetcher_names)
        self.assertIn("StartupDirectory", fetcher_names)

    def test_excel_export(self):
        c = Company(
            name="Lucidya",
            website="https://lucidya.com",
            country="Saudi Arabia",
            city="Riyadh",
            industry="AI",
            category="AI",
            description="AI customer experience tool",
            founding_year=2016,
            employee_count=120,
            funding_stage="Series B",
            total_funding="$8M",
            source="StartupDirectory"
        )
        
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "test_export.xlsx")
            export_to_excel([c], file_path)
            
            # Verify file exists
            self.assertTrue(os.path.exists(file_path))
            
            # Read sheet to verify structure
            df = pd.read_excel(file_path, sheet_name="Companies")
            self.assertEqual(len(df), 1)
            self.assertEqual(df.iloc[0]["Company Name"], "Lucidya")

if __name__ == "__main__":
    unittest.main()
