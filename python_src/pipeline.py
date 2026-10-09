"""Independent validation entrypoint; reports are generated only after parity."""
import argparse
import logging
from .config import OUT
from .database import load_raw, save_json
from . import kpi,retention,funnel,churn,segmentation,reactivation,data_quality,parity,diagnostics

def main() -> None:
    parser=argparse.ArgumentParser();parser.add_argument('--report-only',action='store_true')
    parser.add_argument('--independent-only',action='store_true',help='Compute Python artifacts from existing PostgreSQL facts; skip dual-engine parity and presentation')
    parser.add_argument('--python-only',action='store_true',help='Complete Python analysis, plots, experiment plans and current-run portfolio')
    args=parser.parse_args()
    if args.report_only and args.independent_only:parser.error('--report-only and --independent-only are mutually exclusive')
    logging.basicConfig(level=logging.INFO,format='%(asctime)s %(message)s')
    if not args.report_only:
        data_quality.calculate();logging.info('Loading PostgreSQL raw facts')
        raw=load_raw();metrics={}
        for module in [kpi,retention,funnel,churn,segmentation,reactivation]:
            logging.info('Independent %s',module.__name__);module.calculate(raw,metrics)
        diagnostics.calculate(raw,metrics)
        save_json(OUT/'metrics/python.json',metrics)
    if args.independent_only:
        logging.info('Python analysis complete; parity / shared presentation NOT_APPLICABLE: Wolfram did not run in this invocation')
        return
    if args.python_only:
        from .presentation import python_tables, assets, pdf
        from . import visualization, report
        python_tables(raw,metrics)
        report.generate('python',False)
        visualization.generate('python',False)
        assets('python');pdf()
        return
    logging.info('Parity acceptance gate');parity.check()
    from . import visualization,report
    visualization.generate();report.generate()
    logging.info('Independent validation and portfolio complete')

if __name__=='__main__': main()
