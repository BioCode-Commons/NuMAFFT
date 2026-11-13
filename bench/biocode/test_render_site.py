import unittest

from render_site import upsert_project


class WebsiteIntegrationTests(unittest.TestCase):
    def test_preserves_existing_projects_and_content(self):
        original = '<header>Keep title</header><section id="projects"><table aria-label="Maintained pipeline summary"><tbody><tr><td>NuSTAR measured results</td></tr></tbody></table><article>NuTRF evidence</article></section><footer>Keep footer</footer>'
        project = '<article class="project" aria-labelledby="project-numafft"><h3 id="project-numafft">NuMAFFT</h3></article>'
        row = '<tr id="overview-numafft"><td>NuMAFFT row</td></tr>'
        first = upsert_project(original, project, row)
        self.assertIn('<tr><td>NuSTAR measured results</td></tr>', first)
        self.assertIn('<article>NuTRF evidence</article>', first)
        self.assertTrue(first.startswith('<header>Keep title</header>'))
        self.assertTrue(first.endswith('<footer>Keep footer</footer>'))
        second = upsert_project(first, project, row)
        self.assertEqual(first, second)
        self.assertEqual(second.count('id="overview-numafft"'), 1)
        self.assertEqual(second.count('id="project-numafft"'), 1)

    def test_missing_summary_table_fails_instead_of_rewriting_the_site(self):
        with self.assertRaisesRegex(ValueError, 'summary table'):
            upsert_project('<section id="projects"></section>', '<article>New</article>', '<tr>New</tr>')


if __name__ == '__main__':
    unittest.main()
