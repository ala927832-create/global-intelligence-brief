"""EIA HTML primary-data history reader: no fabricated history, fixed comparisons."""
import datetime as dt
import unittest
from scripts.eia_official_html_history_qa import parse_history,summarize_history

class EIAFullHistoryTests(unittest.TestCase):
    def test_full_series_reconstruction_and_1998_ranking(self):
        rows=[]
        day=dt.date(1990,11,2)
        groups={}
        while day<=dt.date(2026,10,16):
            groups.setdefault((day.year,day.strftime("%b")),[]).append(day)
            day+=dt.timedelta(days=7)
        for (year,month),dates in sorted(groups.items()):
            series=[]
            for day in dates:
                value=97.0 if year==1998 else (95.4 if year==2026 else 92.0)
                series.append(f"<td>{day:%m/%d}</td><td>{value:.1f}</td>")
            rows.append(f"<tr><td>{year}-{month}</td>"+ "".join(series)+"</tr>")
        body="<html><body><table>"+ "".join(rows)+"</table></body></html>"
        parsed=parse_history(body)
        self.assertGreater(len(parsed),1700)
        result=summarize_history(parsed,as_of=dt.date(2026,10,24))
        self.assertTrue(result["matches_2026_highest_since_1998_under_this_method"])
        self.assertFalse(result["human_signed"])
        self.assertFalse(result["release_approved"])
        self.assertEqual(result["years"],36)

    def test_incomplete_history_fails_closed(self):
        body="<table><tr><td>2026-May</td><td>05/01</td><td>95.4</td></tr></table>"
        with self.assertRaises(ValueError):
            parse_history(body)

if __name__=="__main__":
    unittest.main()
