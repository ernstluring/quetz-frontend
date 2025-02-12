import {
  JupyterFrontEnd,
  JupyterFrontEndPlugin,
  IRouter,
} from '@jupyterlab/application';

import { DOMUtils, ReactWidget } from '@jupyterlab/apputils';

import { ServerConnection } from '@jupyterlab/services';

import { URLExt } from '@jupyterlab/coreutils';

import { FetchHoc, formatPlural } from '@quetz-frontend/apputils';

import { List } from '@quetz-frontend/table';

import { FontAwesomeIcon } from '@fortawesome/react-fontawesome';

import {
  faGlobeAmericas,
  faUnlockAlt,
} from '@fortawesome/free-solid-svg-icons';

import ReactTooltip from 'react-tooltip';

import * as React from 'react';

export namespace CommandIDs {
  export const plugin = '@quetz-frontend/home-extension:home';
  export const open = '@quetz-frontend/home-extension:home/open';
}

const plugin: JupyterFrontEndPlugin<void> = {
  id: CommandIDs.plugin,
  autoStart: true,
  requires: [IRouter],
  activate: (app: JupyterFrontEnd, router: IRouter): void => {
    const { shell, commands } = app;

    commands.addCommand(CommandIDs.open, {
      execute: () => {
        shell.add(new Homepage(router), 'main');
      },
    });

    router.register({
      pattern: /home.*/,
      command: CommandIDs.open,
    });
  },
};

export default plugin;

class Homepage extends ReactWidget {
  constructor(router: IRouter) {
    super();
    this.id = DOMUtils.createDomID();
    this.title.label = 'Home page';

    this._router = router;
  }

  private _route(route: string): void {
    this._router.navigate(route);
  }

  render(): JSX.Element {
    const settings = ServerConnection.makeSettings();
    const url = URLExt.join(settings.baseUrl, '/api/channels');

    return (
      <div className="page-contents-width-limit">
        <h2 className="heading2">Home</h2>
        <div className="flex">
          <h3 className="section-heading">Recently updated channels</h3>
          &emsp;
          <p className="minor-paragraph">
            <a className="link" onClick={() => this._route('/channels')}>
              View all
            </a>
          </p>
        </div>
        <div className="padding-side">
          <FetchHoc
            url={url}
            loadingMessage="Fetching list of channels"
            genericErrorMessage="Error fetching list of channels"
          >
            {(channels: any) => {
              return channels.length > 0 ? (
                <List
                  data={channels.slice(0, 5)}
                  columns={getChannelsListColumns()}
                  to={(rowData: any) =>
                    this._route(`/channels/${rowData.name}`)
                  }
                />
              ) : (
                <p className="paragraph">No channels available</p>
              );
            }}
          </FetchHoc>
        </div>
      </div>
    );
  }

  private _router: IRouter;
}

const getChannelsListColumns = (): any => [
  {
    Header: '',
    accessor: 'name',
    Cell: ({ row }: any) =>
      (
        <>
          <span
            data-for={`tooltip-${row.original.name}`}
            data-tip={row.original.private ? 'Private' : 'Public'}
          >
            <FontAwesomeIcon
              icon={row.original.private ? faUnlockAlt : faGlobeAmericas}
            />
          </span>
          <ReactTooltip
            id={`tooltip-${row.original.name}`}
            place="right"
            type="dark"
            effect="solid"
          />
        </>
      ) as any,
    width: 5,
  },
  {
    Header: '',
    accessor: 'user.profile.name',
    Cell: ({ row }: any) =>
      (
        <div>
          <p className="text">{row.original.name}</p>
          <p className="minor-paragraph channel-list-description">
            {row.original.description}
          </p>
        </div>
      ) as any,
    width: 45,
  },
  {
    Header: '',
    accessor: 'user.username',
    Cell: ({ row }: any) =>
      formatPlural(row.original.packages_count, 'package'),
    width: 35,
  },
  {
    Header: '',
    accessor: 'role',
    Cell: ({ row }: any) => formatPlural(row.original.members_count, 'member'),
    width: 20,
  },
];
